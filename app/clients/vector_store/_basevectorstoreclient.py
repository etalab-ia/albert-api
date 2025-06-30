from abc import ABC, abstractmethod
import importlib
from typing import List, Optional, Type

from app.schemas.chunks import Chunk
from app.schemas.search import Search, SearchMethod
from app.schemas.core.settings import DatabaseType


class BaseVectorStoreClient(ABC):
    """Abstract base class for all vector store clients (Elasticsearch, Qdrant, ...)."""

    def __init__(self, *args, **kwargs):
        self.model = kwargs.get('model', None)

    @staticmethod
    def import_module(database_type: DatabaseType) -> "Type[BaseVectorStoreClient]":
        """Dynamically import and return the concrete client class corresponding to *type*.

        Example:
            >>> client_cls = BaseVectorStoreClient.import_module(DatabaseType.ELASTICSEARCH)
            >>> client = client_cls(url="http://localhost:9200")
        """
        module = importlib.import_module(f"app.clients.vector_store._{database_type.value}vectorstoreclient")

        return getattr(module, f"{database_type.capitalize()}VectorStoreClient")

    # ---------------------------------------------------------------------
    # Mandatory lifecycle helpers
    # ---------------------------------------------------------------------
    @abstractmethod
    async def check(self) -> bool:
        """Check the health of the underlying vector store connection."""

    @abstractmethod
    async def close(self) -> None:
        """Cleanly close the underlying connection/pool."""

    # ---------------------------------------------------------------------
    # Collection helpers
    # ---------------------------------------------------------------------
    @abstractmethod
    async def create_collection(self, collection_id: int, vector_size: int) -> None:
        """Create a new collection (index) inside the vector store."""

    @abstractmethod
    async def delete_collection(self, collection_id: int) -> None:
        """Delete a collection (index) from the vector store."""

    @abstractmethod
    async def get_collections(self) -> list[int]:
        """Return the list of existing collection identifiers."""

    # ---------------------------------------------------------------------
    # Document / Chunk helpers
    # ---------------------------------------------------------------------
    @abstractmethod
    async def get_chunk_count(self, collection_id: int, document_id: int) -> Optional[int]:
        """Return the number of chunks for *document_id* inside *collection_id* (or *None* if unavailable)."""

    @abstractmethod
    async def delete_document(self, collection_id: int, document_id: int) -> None:
        """Delete every chunk belonging to *document_id* inside *collection_id*."""

    @abstractmethod
    async def get_chunks(
        self,
        collection_id: int,
        document_id: int,
        offset: int = 0,
        limit: int = 10,
        chunk_id: Optional[int] = None,
    ) -> List[Chunk]:
        """Retrieve a slice of chunks for *document_id* from *collection_id*."""

    @abstractmethod
    async def upsert(self, collection_id: int, chunks: List[Chunk], embeddings: List[list[float]]) -> None:
        """Insert or update *chunks* along with their *embeddings* inside *collection_id*."""

    # ---------------------------------------------------------------------
    # Search
    # ---------------------------------------------------------------------
    @abstractmethod
    async def search(
        self,
        method: SearchMethod,
        collection_ids: List[int],
        query_prompt: str,
        query_vector: list[float],
        k: int,
        rff_k: Optional[int] = 20,
        score_threshold: float = 0.0,
    ) -> List[Search]:
        """Run a search query and return a ranked list of *Search* results."""
