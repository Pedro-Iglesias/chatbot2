"""Abstract interface for embedding providers."""
from abc import ABC, abstractmethod
from typing import List


class EmbeddingProvider(ABC):
    """Gera representações vetoriais (embeddings) para textos."""

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Retorna o vetor de embedding para um texto."""

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Retorna vetores de embedding para uma lista de textos."""