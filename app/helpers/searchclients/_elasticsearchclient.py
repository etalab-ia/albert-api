from typing import List, Literal, Optional
import functools
import time

from concurrent.futures import ThreadPoolExecutor
from elasticsearch import Elasticsearch

from app.helpers.searchclients._searchclient import SearchClient
from app.schemas.collections import Collection
from app.schemas.documents import Document
from app.schemas.chunks import Chunk
from app.schemas.security import User
from app.schemas.search import Filter, Search
from app.utils.exceptions import DifferentCollectionsModelsException
from app.utils.variables import HYBRID_SEARCH_TYPE, LEXICAL_SEARCH_TYPE, SEMANTIC_SEARCH_TYPE


def collate_ix_name(name: str, version: str):
    # Forge the collection name alias.
    if version:
        return "-".join([name, version])
    return name


def retry(tries: int = 3, delay: int = 2):
    """
    A simple retry decorator that catch exception to retry multiple times
    @TODO: only catch only network error/timeout error.

    Parameters:
    - tries: Number of total attempts.
    - delay: Delay between retries in seconds.
    """

    def decorator_retry(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts = tries
            while attempts > 1:
                try:
                    return func(*args, **kwargs)
                # @TODO: Catch network error.
                # except (requests.exceptions.RequestException, httpx.RequestError) as e:
                except Exception as e:
                    print(f"Error: {e}, retrying in {delay} seconds...")
                    time.sleep(delay)
                    attempts -= 1
            # Final attempt without catching exceptions
            return func(*args, **kwargs)

        return wrapper

    return decorator_retry


class ElasticSearchClient(Elasticsearch, SearchClient):
    HYBRID_LIMIT_FACTOR = 1.5

    def __init__(self, models, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.models = models

    def upsert(self, chunks: List[Chunk], collection_id: str, user: User) -> None:
        pass

    def query(
        self,
        prompt: str,
        user: User,
        collection_ids: List[str] = [],
        method: Literal[HYBRID_SEARCH_TYPE, LEXICAL_SEARCH_TYPE, SEMANTIC_SEARCH_TYPE] = SEMANTIC_SEARCH_TYPE,
        k: Optional[int] = 4,
        score_threshold: Optional[float] = None,
        filter: Optional[Filter] = None,  # TODO: implement filter
    ) -> List[Search]:
        index = collate_ix_name(",".join(collection_ids), "v1")
        if method == LEXICAL_SEARCH_TYPE:
            return self._lexical_query(prompt, index, k)
        else:
            embedding = self._create_embedding(prompt, collection_ids, user)
            if method == SEMANTIC_SEARCH_TYPE:
                return self._semantic_query(embedding, index, k)
            elif method == HYBRID_SEARCH_TYPE:
                return self._hybrid_query(embedding, index, k)
        raise ValueError(f"Invalid search method: {method}")

    def _build_query_filter(self, prompt: str):
        fuzziness = {}
        if len(prompt.split()) < 25:
            fuzziness = {"fuzziness": "AUTO"}
        return {"multi_match": {"query": prompt, "type": "best_fields", "tie_breaker": 0.3, **fuzziness}}

    def _build_lexical_query_body(self, prompt: str, limit: int) -> dict:
        return {
            "query": self._build_query_filter(prompt),
            "size": int(limit * self.HYBRID_LIMIT_FACTOR),
            "_source": {"excludes": ["embedding"]},
        }

    def _build_semantic_query_body(self, prompt: str, embedding: list[float], limit: int) -> dict:
        return {
            "knn": {
                "field": "embedding",
                "query_vector": embedding,
                "k": int(limit * self.HYBRID_LIMIT_FACTOR),
                "num_candidates": 200,
                "filter": self._build_query_filter(prompt),
            }
        }

    def _lexical_query(self, prompt: str, index, size: int = 4) -> List[Search]:
        body = {"query": self._build_query_filter(prompt), "size": size}
        results = self.search(index=index, body=body)
        hits = [x.get("_source") for x in results["hits"]["hits"] if x]
        searches = hits
        return searches

    def _hybrid_query(self, prompt: str, embedding: list[float], index: str, limit: int = 4) -> List[Search]:
        # See also: https://elasticsearch-py.readthedocs.io/en/v8.14.0/async.html
        with ThreadPoolExecutor(max_workers=2) as executor:
            lexical_query_body = self._build_lexical_query_body(prompt, limit)
            semantic_query_body = self._build_semantic_query_body(prompt, embedding, limit)
            lexical_future = executor.submit(self.search, index, lexical_query_body)
            semantic_future = executor.submit(self.search, index, semantic_query_body)
            lexical_hits = [x for x in lexical_future.result()["hits"]["hits"] if x]
            semantic_hits = [x for x in semantic_future.result()["hits"]["hits"] if x]

        results = self._rrf_ranker([lexical_hits, semantic_hits], limit=limit)
        hits = [x.get("_source") for x in results]
        return hits

    def _semantic_query(self, prompt: str, embedding: list[float], index: str, limit: int) -> List[Search]:
        # See also: https://elasticsearch-py.readthedocs.io/en/v8.14.0/async.html
        with ThreadPoolExecutor(max_workers=2) as executor:
            semantic_query_body = self._build_semantic_query_body(prompt, embedding, limit)
            semantic_future = executor.submit(self.search, index, semantic_query_body)
            semantic_hits = [x for x in semantic_future.result()["hits"]["hits"] if x]

        results = self._rrf_ranker([semantic_hits], limit=limit)
        hits = [x.get("_source") for x in results]
        return hits

    @retry(tries=3, delay=2)
    def _create_embedding(
        self,
        prompt: str,
        collection_ids: List[str],
        user: User,
    ) -> list[float] | list[list[float]] | dict:
        """
        Simple interface to create an embedding vector from a text input.
        """
        collections = self.get_collections(collection_ids=collection_ids, user=user)
        if len(set(collection.model for collection in collections)) > 1:
            raise DifferentCollectionsModelsException()
        model_client = self.models[collections[0].model]
        response = model_client.embeddings.create(input=[prompt], model=model_client.model)
        return response.data[0].embedding

    def _rrf_ranker(self, group_results, limit: int, k: int = 20):
        """
        Combine search results using Reciprocal Rank Fusion (RRF)
        :param group_results: A list of result lists from different searches
        :param k: The constant k in the RRF formula
        :return: A combined list of results with updated scores
        """
        combined_scores = {}
        doc_map = {}
        for results in group_results:
            for rank, result in enumerate(results):
                doc_id = result["_id"]
                if doc_id not in combined_scores:
                    combined_scores[doc_id] = 0
                    doc_map[doc_id] = result
                combined_scores[doc_id] += 1 / (k + rank + 1)

        # Sort combined results by their RRF scores in descending order
        ranked_results = sorted(combined_scores.items(), key=lambda item: item[1], reverse=True)
        reranked_results = []
        for doc_id, rrf_score in ranked_results:
            document = doc_map[doc_id]
            document["_rff_score"] = rrf_score
            reranked_results.append(document)

        return reranked_results[:limit]

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

    def delete_document(self, document_id: str, user: User) -> None:
        pass
