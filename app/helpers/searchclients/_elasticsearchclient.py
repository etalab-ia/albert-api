from typing import List, Optional

from app.helpers.searchclients._searchclient import SearchClient
from app.schemas.collection import Collection
from app.schemas.document import Document
from app.schemas.chunk import Chunk
from app.schemas.filter import Filter
from app.schemas.security import User
from app.schemas.search import Search


class ElasticSearchClient(SearchClient):
    def upsert(self, chunks: List[Chunk], collection_id: str, user: User) -> None:
        pass

    def search(
        self,
        prompt: str,
        user: User,
        collection_ids: List[str] = [],
        k: Optional[int] = 4,
        score_threshold: Optional[float] = None,
        filter: Optional[Filter] = None,
    ) -> List[Search]:
        pass

    def get_collections(self, collection_ids: List[str], user: User) -> List[Collection]:
        pass

    def create_collection(self, collection: Collection) -> Collection:
        pass

    def delete_collection(self, collection_id: str, user: User) -> None:
        pass

    def get_chunks(self, collection_id: str, user: User, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Chunk]:
        pass

    def get_documents(self, collection_id: str, user: User, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Document]:
        pass
