from types import SimpleNamespace
from typing import List
import uuid

from app.helpers import InternetManager
from app.schemas.search import Search
from app.schemas.security import User
from app.utils.variables import COLLECTION_DISPLAY_ID__INTERNET


class SearchManager:
    def __init__(self, clients: SimpleNamespace) -> None:
        self.models = clients.models
        self.search_client = clients.search
        self.internet_manager = InternetManager(clients=clients)

    async def query(
        self, collections: List[str], prompt: str, method: str, k: int, rff_k: int, user: User, score_threshold: float = 0.0
    ) -> List[Search]:
        # internet search
        internet_chunks = []
        if COLLECTION_DISPLAY_ID__INTERNET in collections:
            internet_collection_id = str(uuid.uuid4())
            internet_chunks = await self.internet_manager.get_chunks(prompt=prompt, collection_id=internet_collection_id)

            if internet_chunks:
                collections.remove(COLLECTION_DISPLAY_ID__INTERNET)
                internet_model_id = (
                    self.models.internet_default_embeddings_model
                    if not collections
                    else self.search_client.get_collections(collection_ids=collections, user=user)[0].model
                )

                self.search_client.create_collection(
                    collection_id=internet_collection_id,
                    collection_name=internet_collection_id,
                    collection_model=internet_model_id,
                    user=user,
                )
                await self.search_client.upsert(chunks=internet_chunks, collection_id=internet_collection_id, user=user)

                collections.append(internet_collection_id)

            # case: no other collections, only internet and no internet results
            elif collections == [COLLECTION_DISPLAY_ID__INTERNET]:
                return []

        searches = await self.search_client.query(
            prompt=prompt, collection_ids=collections, method=method, k=k, rff_k=rff_k, score_threshold=score_threshold, user=user
        )

        if internet_chunks:
            self.search_client.delete_collection(collection_id=internet_collection_id, user=user)

        if score_threshold:
            searches = [search for search in searches if search.score >= score_threshold]

        return searches
