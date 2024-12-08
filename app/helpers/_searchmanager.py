from typing import List
import uuid

from app.clients import ModelClients, SearchClient
from app.helpers import InternetManager
from app.schemas.search import Search
from app.schemas.security import User
from app.utils.variables import INTERNET_COLLECTION_DISPLAY_ID


class SearchManager:
    def __init__(self, model_clients: ModelClients, search_client: SearchClient, internet_manager: InternetManager) -> None:
        self.model_clients = model_clients
        self.search_client = search_client
        self.internet_manager = internet_manager

    def query(self, collections: List[str], prompt: str, method: str, k: int, rff_k: int, user: User, score_threshold: float = 0.0) -> List[Search]:
        # internet search
        internet_chunks = []
        if INTERNET_COLLECTION_DISPLAY_ID in collections:
            internet_collection_id = str(uuid.uuid4())
            internet_chunks = self.internet_manager.get_chunks(prompt=prompt, collection_id=internet_collection_id)

            if internet_chunks:
                collections.remove(INTERNET_COLLECTION_DISPLAY_ID)
                internet_embeddings_model_id = (
                    self.internet_manager.default_embeddings_model_id
                    if not collections
                    else self.search_client.get_collections(collection_ids=collections, user=user)[0].model
                )

                self.search_client.create_collection(
                    collection_id=internet_collection_id,
                    collection_name=internet_collection_id,
                    collection_model=internet_embeddings_model_id,
                    user=user,
                )
                self.search_client.upsert(chunks=internet_chunks, collection_id=internet_collection_id, user=user)

                collections.append(internet_collection_id)

            # case: no other collections, only internet and no internet results
            elif collections == [INTERNET_COLLECTION_DISPLAY_ID]:
                return []

        searches = self.search_client.query(
            prompt=prompt, collection_ids=collections, method=method, k=k, rff_k=rff_k, score_threshold=score_threshold, user=user
        )

        if internet_chunks:
            self.search_client.delete_collection(collection_id=internet_collection_id, user=user)

        if score_threshold:
            searches = [search for search in searches if search.score >= score_threshold]

        return searches
