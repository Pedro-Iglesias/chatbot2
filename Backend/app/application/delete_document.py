"""
Caso de uso: excluir um documento pelo ID.
Recebe o repositório via injeção de dependência (vindo da Factory).
"""

from Backend.app.domain.repositories.document_repository import DocumentRepository


class DeleteDocument:

    def __init__(self, repository: DocumentRepository):
        self.repository = repository

    def executar(self, id_documento: int) -> dict:
        if not isinstance(id_documento, int) or id_documento <= 0:
            raise ValueError("ID do documento inválido.")

        documento = self.repository.get_by_id(id_documento)

        if documento is None:
            raise LookupError(f"Documento com ID {id_documento} não encontrado.")

        self.repository.delete(id_documento)

        return {
            "message": f"Documento '{documento.nome}' excluído com sucesso.",
            "id": id_documento,
        }