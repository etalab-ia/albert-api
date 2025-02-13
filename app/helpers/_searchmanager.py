from typing import List
import uuid

from app.clients.internet import BaseInternetClient as InternetClient
from app.clients.search import BaseSearchClient as SearchClient
from app.helpers import InternetManager, ModelRegistry
from app.schemas.search import Search
from app.schemas.security import User
from app.utils.variables import COLLECTION_DISPLAY_ID__INTERNET


class SearchManager:
    def __init__(self, models: ModelRegistry, search: SearchClient, internet: InternetClient) -> None:
        """
        SearchManager is a helper class that manages the vector search.

        Args:
            models (SimpleNamespace): The models namespace from the lifespan event.
            databases (SimpleNamespace): The databases namespace from the lifespan event.
            internet (SimpleNamespace): The internet namespace from the lifespan event.
        """
        self.models = models
        self.search = search
        self.internet_manager = InternetManager(models=models, internet=internet)

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
                    else self.search.get_collections(collection_ids=collections, user=user)[0].model
                )

                self.search.create_collection(
                    collection_id=internet_collection_id,
                    collection_name=internet_collection_id,
                    collection_model=internet_model_id,
                    user=user,
                )
                await self.search.upsert(chunks=internet_chunks, collection_id=internet_collection_id, user=user)

                collections.append(internet_collection_id)

            # case: no other collections, only internet and no internet results
            elif collections == [COLLECTION_DISPLAY_ID__INTERNET]:
                return []

        searches = await self.search.query(
            prompt=prompt, collection_ids=collections, method=method, k=k, rff_k=rff_k, score_threshold=score_threshold, user=user
        )

        if internet_chunks:
            self.search.delete_collection(collection_id=internet_collection_id, user=user)

        if score_threshold:
            searches = [search for search in searches if search.score >= score_threshold]

        return searches
