from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Document:
    id: str
    content: str
    metadata: dict
    score: float | None = None


@dataclass
class CollectionStats:
    count: int
    name: str


class VectorStore(ABC):
    @abstractmethod
    async def add_texts(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> list[str]:
        ...

    @abstractmethod
    async def similarity_search(
        self,
        query_embedding: list[float],
        k: int = 5,
        score_threshold: float = 0.0,
    ) -> list[Document]:
        ...

    @abstractmethod
    async def delete_document(self, document_id: str) -> None:
        ...

    @abstractmethod
    async def get_collection_stats(self) -> CollectionStats:
        ...
