"""Caso de uso: responder pergunta do usuário usando o banco de documentos."""
import math
import re
import unicodedata
from typing import List, Optional

import google.generativeai as genai
from django.conf import settings

from Backend.app.application.embedding_provider import EmbeddingProvider
from Backend.app.documents.models import Conversa, Mensagem, Documento, ChunkDocumento
from Backend.app.domain.repositories.chunk_repository import ChunkRepository

# Instrui o modelo a responder sempre com citações explícitas do documento de origem
_PROMPT_TEMPLATE = """\
Você é um assistente especializado em documentos institucionais do IFES.
Responda à pergunta priorizando os trechos abaixo, em português.
Você pode combinar informações de múltiplos trechos para produzir uma resposta mais completa e analítica.
Se os trechos não forem suficientes, ainda assim responda de forma útil, transparente e sem inventar detalhes específicos que não estejam confirmados.
Quando fizer sentido, explique em 2 a 4 parágrafos curtos: primeiro responda objetivamente, depois detalhe a base documental, e por fim aponte limites ou observações relevantes.

Regras obrigatórias:
1. Sempre cite o documento de origem na resposta quando houver trechos recuperados, usando o formato:
   "Segundo o documento [NOME DO DOCUMENTO], página [N], ..."
   ou "Conforme [NOME DO DOCUMENTO] (pág. [N]), ..."
2. Se uma informação vier de mais de um documento, cite todos.
3. Se a informação não estiver totalmente confirmada no contexto, explique a incerteza sem encerrar a resposta.
4. Se nenhum trecho relevante for recuperado, responda de forma útil e transparente, sem inventar detalhes documentais.
5. Evite respostas secas ou genéricas; prefira contextualizar o significado do documento, o alcance da regra e, quando cabível, as implicações práticas.

Contexto:
{contexto}

Pergunta: {pergunta}

Resposta:"""

_MENSAGEM_SEM_RESPOSTA = (
    "Não encontrei confirmação suficiente nos documentos disponíveis, mas posso tentar "
    "explicar com base no que foi recuperado."
)
_MENSAGEM_SEM_DOCUMENTOS = (
    "Ainda não há documentos indexados na base de conhecimento. "
    "Adicione documentos antes de fazer perguntas."
)
_MENSAGEM_ERRO_API = (
    "Não foi possível processar sua pergunta no momento. "
    "Verifique sua conexão e tente novamente."
)
_MENSAGEM_COTA_API = (
    "A cota da API Gemini foi excedida no momento. "
    "Aguarde alguns minutos e tente novamente."
)

_ALIAS_TERMINOS = {
    "rods": "rod",
    "rod's": "rod",
    "portarias": "portaria",
    "resolucoes": "resolucao",
    "resoluções": "resolucao",
    "neabi": "nucleo estudos afrobrasileiros e indigenas",
    "scdp": "sistema concessao diarias passagens",
    "tri": "treinamento regularmente instituido",
    "progressao": "progressao",
    "progressão": "progressao",
    "titulacao": "titulacao",
    "titulação": "titulacao",
    "ferias": "ferias",
    "férias": "ferias",
}

# Tamanho máximo do trecho de citação exibido no frontend
_TRECHO_MAX_CHARS = 220

# Cache simples em memória para reduzir chamadas repetidas ao serviço de embedding.
_EMBEDDING_CACHE: dict[tuple[str, str, str], List[float]] = {}


# ─── Pré-processamento ────────────────────────────────────────────────────────

def preprocessar_pergunta(texto: str) -> str:
    texto = texto.strip()
    texto = re.sub(r'\s+', ' ', texto)
    texto = texto.lower()
    texto = re.sub(r'[^\w\s\?\!\.\,\á\é\í\ó\ú\ã\õ\â\ê\ô\ç]', '', texto)

    # Normaliza siglas e plurais comuns para melhorar a recuperação semântica.
    for origem, destino in _ALIAS_TERMINOS.items():
        texto = re.sub(rf'\b{re.escape(origem)}\b', destino, texto)

    return texto


def gerar_titulo_conversa(pergunta: str, max_palavras: int = 8) -> str:
    """Gera um título curto e legível a partir da primeira pergunta útil."""
    pergunta = preprocessar_pergunta(pergunta)
    palavras_pra_ignorar = {
        "oi", "olá", "ola", "bom", "dia", "boa", "tarde", "noite",
        "obrigado", "obrigada", "valeu", "por", "favor", "me",
        "qual", "quais", "quando", "onde", "como", "quem", "que",
        "o", "a", "os", "as", "um", "uma", "pra", "pro", "para",
    }
    palavras = [
        palavra for palavra in re.findall(r"[\wáéíóúãõâêôç]+", pergunta, flags=re.IGNORECASE)
        if palavra not in palavras_pra_ignorar
    ]
    if not palavras:
        return "Nova conversa"
    titulo = " ".join(palavras[:max_palavras]).strip()
    if len(palavras) > max_palavras:
        titulo += "..."
    titulo = titulo.rstrip("?!.:,;")
    return titulo[:1].upper() + titulo[1:]


def _extrair_trecho(conteudo: str, max_chars: int = _TRECHO_MAX_CHARS) -> str:
    """Extrai um trecho representativo do chunk para exibir como citação."""
    conteudo = conteudo.strip()
    if len(conteudo) <= max_chars:
        return conteudo
    trecho = conteudo[:max_chars]
    ultimo_espaco = trecho.rfind(' ')
    if ultimo_espaco > max_chars // 2:
        trecho = trecho[:ultimo_espaco]
    return trecho + "…"


def _label_pagina(numero_pagina: Optional[int]) -> str:
    """Retorna a label de página para o contexto do prompt."""
    return f"Página {numero_pagina}" if numero_pagina else "Página N/A"


def _is_quota_error(exc: Exception) -> bool:
    texto = str(exc).lower()
    return "quota exceeded" in texto or "resource_exhausted" in texto or "429" in texto


def _tipo_documento_prioritario(pergunta: str) -> Optional[str]:
    pergunta_normalizada = preprocessar_pergunta(pergunta)
    tokens = set(re.findall(r"[\wáéíóúãõâêôç]+", pergunta_normalizada, flags=re.IGNORECASE))

    if "rod" in tokens:
        return "rod"
    if "resolucao" in tokens:
        return "resolucao"
    if "portaria" in tokens:
        return "portaria"
    return None


def _priorizar_candidatos_por_tipo(candidates: List[dict], tipo_prioritario: Optional[str]) -> List[dict]:
    if not tipo_prioritario:
        return candidates

    candidatos_prioritarios = [c for c in candidates if c.get("documento_tipo") == tipo_prioritario]
    if candidatos_prioritarios:
        return sorted(candidatos_prioritarios, key=lambda item: item["score"], reverse=True)

    candidatos_ajustados: List[dict] = []
    for candidate in candidates:
        adjusted = dict(candidate)
        adjusted["score"] = float(candidate["score"])
        candidatos_ajustados.append(adjusted)

    return sorted(candidatos_ajustados, key=lambda item: item["score"], reverse=True)


def _obter_embedding_cacheado(
    embedding_provider: EmbeddingProvider,
    texto: str,
    task_type: str,
) -> List[float]:
    chave = (
        texto,
        task_type,
        getattr(settings, "EMBEDDING_MODEL", ""),
    )
    if chave not in _EMBEDDING_CACHE:
        _EMBEDDING_CACHE[chave] = embedding_provider.embed(texto, task_type=task_type)
    return _EMBEDDING_CACHE[chave]


# ─── MMR (Maximal Marginal Relevance) re-ranking ─────────────────────────────

def _cosine(a: List[float], b: List[float]) -> float:
    """Similaridade de cosseno entre dois vetores."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _mmr_rerank(
    candidates: List[dict],
    top_k: int,
    lambda_mult: float = 0.6,
) -> List[dict]:
    """
    Maximal Marginal Relevance: seleciona *top_k* chunks equilibrando
    relevância para a query (score pgvector) e diversidade entre si.
    """
    if len(candidates) <= top_k:
        selected = candidates
    else:
        selected: List[dict] = []
        remaining = list(candidates)

        while len(selected) < top_k and remaining:
            if not selected:
                best = max(remaining, key=lambda c: c["score"])
            else:
                def mmr_score(c: dict) -> float:
                    max_sim = max(
                        _cosine(c["embedding"], s["embedding"]) for s in selected
                    )
                    return lambda_mult * c["score"] - (1 - lambda_mult) * max_sim

                best = max(remaining, key=mmr_score)

            selected.append(best)
            remaining.remove(best)

    return [{k: v for k, v in c.items() if k != "embedding"} for c in selected]


# ─── Montagem do contexto com rótulos de documento/página ────────────────────

def _montar_contexto(chunks: List[dict]) -> str:
    """
    Monta o bloco de contexto para o prompt, rotulando cada trecho com
    o nome do documento e a página — informações que o modelo usará para
    produzir as citações.
    """
    blocos = []
    for chunk in chunks:
        pagina = _label_pagina(chunk.get("numero_pagina"))
        header = f"[Documento: {chunk['documento_nome']} | {pagina}]"
        blocos.append(f"{header}\n{chunk['conteudo']}")
    return "\n\n---\n\n".join(blocos)


def _construir_citacoes(chunks: List[dict]) -> List[dict]:
    """
    Constrói a lista de citações estruturadas a partir dos chunks usados.
    Cada citação representa um trecho relevante de um documento específico.
    """
    citacoes = []
    for ordem, chunk in enumerate(chunks, start=1):
        citacoes.append({
            "ordem":          ordem,
            "documento_id":   chunk["documento_id"],
            "documento_nome": chunk["documento_nome"],
            "numero_pagina":  chunk.get("numero_pagina"),
            "trecho":         _extrair_trecho(chunk["conteudo"]),
        })
    return citacoes


def _determinar_documento_principal(chunks: List[dict]) -> Optional[dict]:
    if not chunks:
        return None

    contagem: dict[str, int] = {}
    for chunk in chunks:
        tipo = chunk.get("documento_tipo") or "desconhecido"
        contagem[tipo] = contagem.get(tipo, 0) + 1

    tipo_principal = max(contagem.items(), key=lambda item: item[1])[0]

    for chunk in chunks:
        if (chunk.get("documento_tipo") or "desconhecido") == tipo_principal:
            return {
                "tipo": tipo_principal,
                "nome": chunk.get("documento_nome"),
            }

    primeiro = chunks[0]
    return {
        "tipo": primeiro.get("documento_tipo") or "desconhecido",
        "nome": primeiro.get("documento_nome"),
    }


def _resposta_local_por_chunks(pergunta: str, chunks: List[dict]) -> str:
    if not chunks:
        return (
            "Encontrei a pergunta, mas não consegui recuperar trechos suficientes dos documentos para montar "
            "uma resposta segura no momento. Tente reformular ou escolha um termo mais específico."
        )

    documento_principal = _determinar_documento_principal(chunks)
    nome_documento = documento_principal["nome"] if documento_principal else chunks[0].get("documento_nome", "documento consultado")

    def normalizar_texto(texto: str) -> str:
        texto = re.sub(r"\s+", " ", texto).strip()
        texto = texto.replace("–", "-").replace("—", "-")
        texto = unicodedata.normalize("NFKD", texto)
        texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
        return texto

    def extrair_definicao_direta(termo: str) -> Optional[str]:
        for chunk in chunks:
            conteudo = normalizar_texto(chunk["conteudo"])
            if termo.lower() == "rod" and "regulamento da organizacao didatica" in conteudo.lower():
                if "cursos tecnicos" in conteudo.lower():
                    return "Regulamento da Organização Didática dos Cursos Técnicos do Ifes"
                if "cursos de graduacao" in conteudo.lower() or "cursos de graduação" in conteudo.lower():
                    return "Regulamento da Organização Didática dos Cursos de Graduação do Ifes"
                return "Regulamento da Organização Didática do Ifes"
        return None

    if re.search(r"\brod\b", pergunta, flags=re.IGNORECASE):
        definicao = extrair_definicao_direta("ROD")
        if definicao:
            return (
                f"ROD significa {definicao}. "
                "No material consultado, ele é descrito como o documento que estabelece normas aos processos didáticos e pedagógicos do Ifes."
            )

    if re.search(r"\bresolucao\b", pergunta, flags=re.IGNORECASE):
        resumo = " "
        if chunks:
            trecho = _extrair_trecho(chunks[0]["conteudo"], max_chars=220)
            resumo = f" No documento consultado, o conteúdo mais relevante encontrado foi: {trecho}."
        return (
            f"Resolução, no contexto dos documentos do Ifes, é um ato normativo usado para formalizar diretrizes, regras ou decisões institucionais.{resumo}"
        )

    if re.search(r"\bportaria\b", pergunta, flags=re.IGNORECASE):
        resumo = " "
        if chunks:
            trecho = _extrair_trecho(chunks[0]["conteudo"], max_chars=220)
            resumo = f" No documento consultado, o conteúdo mais relevante encontrado foi: {trecho}."
        return (
            f"Portaria, no contexto dos documentos do Ifes, é um ato administrativo usado para registrar decisões, determinações ou providências institucionais.{resumo}"
        )

    trechos = []
    for chunk in chunks[:2]:
        trecho = _extrair_trecho(chunk["conteudo"], max_chars=170)
        if trecho:
            pagina = _label_pagina(chunk.get("numero_pagina"))
            trechos.append(f"- {chunk['documento_nome']} ({pagina}): {trecho}")

    if not trechos:
        return (
            f"Pelo que consegui recuperar no documento {nome_documento}, a resposta ainda precisa ser interpretada com cuidado. "
            "Não encontrei um trecho suficientemente claro para fechar uma definição completa."
        )

    prefixo = f"Pelo que encontrei no documento {nome_documento}, "
    if re.search(r"\brod\b", pergunta, flags=re.IGNORECASE):
        prefixo = f"Pelo que encontrei sobre ROD no documento {nome_documento}, "
    elif re.search(r"\bresolucao\b", pergunta, flags=re.IGNORECASE):
        prefixo = f"Pelo que encontrei sobre resoluções no documento {nome_documento}, "
    elif re.search(r"\bportaria\b", pergunta, flags=re.IGNORECASE):
        prefixo = f"Pelo que encontrei sobre portarias no documento {nome_documento}, "

    return (
        f"{prefixo}consigo resumir assim: o conteúdo recuperado aponta para este contexto:\n"
        + "\n".join(trechos)
        + "\n\nSe quiser, posso refinar a busca com outro termo do documento para deixar a resposta mais precisa."
    )


def _carregar_chunks_rods_para_definicao(limit: int = 8) -> List[dict]:
    qs = (
        ChunkDocumento.objects
        .select_related("documento")
        .filter(documento__tipo="rod")
        .filter(conteudo__icontains="Regulamento da Organização Didática")
        .order_by("documento_id", "numero_chunk")[:limit]
    )
    return [
        {
            "conteudo": chunk.conteudo,
            "numero_pagina": chunk.numero_pagina,
            "documento_nome": chunk.documento.nome,
            "documento_id": chunk.documento_id,
            "documento_tipo": chunk.documento.tipo,
        }
        for chunk in qs
    ]


# ─── Caso de uso principal ────────────────────────────────────────────────────

class ResponderPergunta:
    """
    Caso de uso: pipeline RAG completo com citações de origem.

    Fluxo:
        1. Gera embedding da pergunta com task_type='retrieval_query'.
        2. Busca os top RERANK_FETCH_K candidatos via pgvector.
        3. Re-ranking MMR para selecionar TOP_K chunks diversos e relevantes.
        4. Monta contexto rotulado (documento + página) e gera resposta via Gemini.
        5. Retorna resposta + fontes + citacoes + respondida.
    """

    def __init__(
        self,
        chunk_repository: ChunkRepository,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._chunk_repo = chunk_repository
        self._embedding_provider = embedding_provider

    def executar(self, pergunta_processada: str) -> dict:
        """
        Retorna dict com:
            - resposta:   str        — texto gerado pelo Gemini (ou mensagem de erro)
            - fontes:     list[dict] — documentos únicos: {id, nome}
            - citacoes:   list[dict] — trechos usados: {ordem, documento_id, documento_nome,
                                        numero_pagina, trecho}
            - respondida: bool       — True se o modelo encontrou resposta no contexto
            - intencao:   str        — 'rag'
        """
        if not settings.GEMINI_API_KEY:
            return self._sem_resposta(_MENSAGEM_ERRO_API)

        try:
            fetch_k = getattr(settings, "RERANK_FETCH_K", max(settings.TOP_K * 2, settings.TOP_K))
            top_k_contexto = max(1, min(getattr(settings, "RAG_CONTEXT_TOP_K", 3), settings.TOP_K))
            tipo_prioritario = _tipo_documento_prioritario(pergunta_processada)

            # 1) Recupera os trechos mais relevantes via embedding sem estreitar
            # a busca por tipo de documento ou palavra-chave específica.
            query_embedding = _obter_embedding_cacheado(
                self._embedding_provider,
                pergunta_processada,
                task_type="retrieval_query",
            )
            if tipo_prioritario and hasattr(self._chunk_repo, "buscar_por_tipo_documento"):
                candidates = self._chunk_repo.buscar_por_tipo_documento(tipo_prioritario, fetch_k)
            else:
                candidates = self._chunk_repo.buscar_candidatos(query_embedding, fetch_k)
                candidates = _priorizar_candidatos_por_tipo(candidates, tipo_prioritario)

            # 3. Re-ranking MMR
            chunks = _mmr_rerank(candidates, top_k=top_k_contexto) if candidates else []

            # 4. Monta contexto e gera resposta
            if chunks:
                contexto = _montar_contexto(chunks)
            else:
                contexto = (
                    "Nenhum trecho relevante foi recuperado pela busca semântica. "
                    "Responda de forma útil e transparente, sem inventar detalhes documentais."
                )
            prompt = _PROMPT_TEMPLATE.format(
                contexto=contexto,
                pergunta=pergunta_processada,
            )

            genai.configure(api_key=settings.GEMINI_API_KEY)
            try:
                model = genai.GenerativeModel(settings.CHAT_MODEL)
                resposta_texto = model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.2,
                        "top_p": 0.9,
                        "max_output_tokens": 420,
                    },
                ).text
            except Exception as exc:
                if _is_quota_error(exc):
                    if tipo_prioritario == "rod":
                        rod_chunks = _carregar_chunks_rods_para_definicao()
                        resposta_texto = _resposta_local_por_chunks(pergunta_processada, rod_chunks or chunks)
                    else:
                        resposta_texto = _resposta_local_por_chunks(pergunta_processada, chunks)
                else:
                    return self._sem_resposta(_MENSAGEM_ERRO_API)

            # 5. Monta fontes (documentos únicos) e citações (trechos individuais)
            fontes = self._deduplicar_fontes(chunks)
            citacoes = _construir_citacoes(chunks)
            documento_principal = _determinar_documento_principal(chunks)

            return {
                "resposta":   resposta_texto,
                "fontes":     fontes,
                "citacoes":   citacoes,
                "documento_principal": documento_principal,
                "respondida": True,
                "intencao":   "rag",
            }

        except Exception as exc:
            if _is_quota_error(exc):
                return self._sem_resposta(_MENSAGEM_COTA_API)
            return self._sem_resposta(_MENSAGEM_ERRO_API)

    # ─── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _sem_resposta(mensagem: str) -> dict:
        return {
            "resposta":   mensagem,
            "fontes":     [],
            "citacoes":   [],
            "documento_principal": None,
            "respondida": False,
            "intencao":   "rag",
        }

    @staticmethod
    def _deduplicar_fontes(chunks: List[dict]) -> List[dict]:
        """Retorna lista de documentos únicos mantendo ordem de relevância."""
        seen: set = set()
        fontes: List[dict] = []
        for chunk in chunks:
            doc_id = chunk["documento_id"]
            if doc_id not in seen:
                seen.add(doc_id)
                fontes.append({"id": doc_id, "nome": chunk["documento_nome"]})
        return fontes


# ─── Helpers de conversa ──────────────────────────────────────────────────────

def iniciar_conversa(user=None) -> Conversa:
    """Cria e retorna uma nova conversa. #34"""
    return Conversa.objects.create(user=user)


def registrar_mensagem(conversa: Conversa, pergunta_original: str) -> Mensagem:
    """Registra a pergunta original (#36) e a processada (#37)."""
    pergunta_processada = preprocessar_pergunta(pergunta_original)
    mensagem = Mensagem.objects.create(
        conversa=conversa,
        role="user",
        conteudo_original=pergunta_original,
        conteudo_processado=pergunta_processada,
    )
    return mensagem


def registrar_resposta(
    conversa: Conversa,
    resposta: str,
    ids_fontes: List[int] | None = None,
) -> Mensagem:
    """
    Registra a resposta do assistente e vincula os documentos de origem.

    Args:
        conversa:   sessão de chat.
        resposta:   texto gerado pelo modelo.
        ids_fontes: IDs dos Documentos usados como contexto RAG.
    """
    mensagem = Mensagem.objects.create(
        conversa=conversa,
        role="assistant",
        conteudo_original=resposta,
        conteudo_processado=resposta,
    )
    if ids_fontes:
        documentos = Documento.objects.filter(id__in=ids_fontes)
        mensagem.fontes.set(documentos)
    return mensagem
