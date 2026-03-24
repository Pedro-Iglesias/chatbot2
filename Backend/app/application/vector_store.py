"""Abstract interface for vector store providers."""
from abc import ABC, abstractmethod
from typing import List, Tuple

# Removido import de chatbot.domain.entities.document (estrutura antiga)
# O modelo concreto é Backend.app.documents.models.Documento
from Backend.app.documents.models import Documento


class VectorStore(ABC):
    """Armazena embeddings de documentos e suporta busca por similaridade."""

    @abstractmethod
    def add_document(self, documento: Documento, embedding: List[float]) -> None:
        """Indexa *documento* com seu *embedding* pré-calculado."""

    @abstractmethod
    def search(
        self, query_embedding: List[float], top_k: int = 5
    ) -> List[Tuple[Documento, float]]:
        """Retorna os *top_k* documentos mais similares com seus scores."""

    @abstractmethod
    def clear(self) -> None:
        """Remove todos os documentos indexados."""