from typing import List, Literal, Optional
import functools
import time

from concurrent.futures import ThreadPoolExecutor
from elasticsearch import Elasticsearch, helpers

from app.helpers.searchclients._searchclient import SearchClient
from app.schemas.collections import Collection
from app.schemas.documents import Document
from app.schemas.chunks import Chunk
from app.schemas.security import User
from app.schemas.search import Filter, FieldCondition, FilterSelector, PointIdsList, MatchAny, Search
from app.utils.exceptions import DifferentCollectionsModelsException, WrongCollectionTypeException, WrongModelTypeException
from app.utils.variables import (
    EMBEDDINGS_MODEL_TYPE,
    HYBRID_SEARCH_TYPE,
    LEXICAL_SEARCH_TYPE,
    SEMANTIC_SEARCH_TYPE,
    ROLE_LEVEL_2,
    PUBLIC_COLLECTION_TYPE,
)


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


class ElasticSearchClient(SearchClient, Elasticsearch):
    def __init__(self, models: List[str] = None, hybrid_limit_factor: float = 1.5, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.models = models
        self.hybrid_limit_factor = hybrid_limit_factor

    def upsert(self, chunks: List[Chunk], collection_id: str, user: User) -> None:
        index = self._build_index(collection_id, user)
        helpers.bulk(self, chunks, index=index)

    def query(
        self,
        prompt: str,
        user: User,
        collection_ids: List[str] = [],
        method: Literal[HYBRID_SEARCH_TYPE, LEXICAL_SEARCH_TYPE, SEMANTIC_SEARCH_TYPE] = SEMANTIC_SEARCH_TYPE,
        k: Optional[int] = 4,
        score_threshold: Optional[float] = None,  # TODO: implement score_threshold
        filter: Optional[Filter] = None,  # TODO: implement filter
    ) -> List[Search]:
        index = self._build_index(collection_ids, user)
        if method == LEXICAL_SEARCH_TYPE:
            return self._lexical_query(prompt, index, k)
        else:
            embedding = self._create_embedding(prompt, collection_ids, user)
            if method == SEMANTIC_SEARCH_TYPE:
                return self._semantic_query(embedding, index, k)
            elif method == HYBRID_SEARCH_TYPE:
                return self._hybrid_query(embedding, index, k)
        raise ValueError(f"Invalid search method: {method}")

    def get_collections(self, user: User, collection_ids: List[str] = []) -> List[Collection]:
        """
        See SearchClient.get_collections
        """
        index_pattern = ",".join(collection_ids)

        collections_by_id = {}
        results = self.indices.get_mapping(index=index_pattern)
        for index_id, result in results.items():
            metadata = result["mappings"].get("_meta")
            if metadata:
                print(index_id, metadata, flush=True)
                collections_by_id[index_id] = Collection(id=index_id, **metadata)

        for indice in self.cat.indices(index=index_pattern, format="json", v=True):
            index = indice["index"]
            if index in collections_by_id:
                collections_by_id[index].documents = int(indice["docs.count"])

        return list(collections_by_id.values())

    def create_collection(self, collection_id: str, collection_name: str, collection_model: str, collection_type: str, user: User) -> None:
        """
        See SearchClient.create_collection
        """
        if self.models[collection_model].type != EMBEDDINGS_MODEL_TYPE:
            raise WrongModelTypeException()

        if user.role != ROLE_LEVEL_2 and collection_type == PUBLIC_COLLECTION_TYPE:
            raise WrongCollectionTypeException()

        index = self._build_index(collection_id, user)
        settings = {
            "similarity": {"default": {"type": "BM25"}},
            "analysis": {
                "filter": {
                    "french_stop": {"type": "stop", "stopwords": "_french_"},
                    "french_stemmer": {"type": "stemmer", "language": "light_french"},
                },
                "analyzer": {
                    "french_analyzer": {
                        "tokenizer": "standard",
                        "filter": ["lowercase", "french_stop", "french_stemmer"],
                    }
                },
            },
        }
        mappings = {
            "properties": {
                "embedding": {"type": "dense_vector", "dims": 1536},
            },
            "_meta": {
                "name": collection_name,
                "type": collection_type,
                "model": collection_model,
                "user": user.id,
                "description": None,
                "created_at": round(time.time()),
                "documents": 0,
            },
        }

        self.indices.create(index=index, mappings=mappings, settings=settings, ignore=400)

    def delete_collection(self, collection_id: str, user: User) -> None:
        """
        See SearchClient.delete_collection
        """
        index = self._build_index(collection_id, user)
        self.indices.delete(index=index, ignore_unavailable=True)

    def get_chunks(self, collection_id: str, user: User, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Chunk]:
        """
        See SearchClient.get_chunks
        """
        pass

    def get_documents(self, collection_id: str, user: User, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Document]:
        """
        See SearchClient.get_document
        """
        collection = self.get_collections(collection_ids=[collection_id], user=user)[0]

        filter = Filter(must=[FieldCondition(key="collection_id", match=MatchAny(any=[collection_id]))])
        data = super().scroll(collection_name=self.DOCUMENT_COLLECTION_ID, scroll_filter=filter, limit=limit, offset=offset)[0]
        documents = list()
        for document in data:
            chunks_count = (
                super()
                .count(
                    collection_name=collection.id,
                    count_filter=Filter(must=[FieldCondition(key="metadata.document_id", match=MatchAny(any=[document.id]))]),
                )
                .count
            )
            documents.append(Document(id=document.id, name=document.payload["name"], created_at=document.payload["created_at"], chunks=chunks_count))

        return documents

    def delete_document(self, collection_id: str, document_id: str, user: User):
        """
        See SearchClient.delete_document
        """
        collection = self.get_collections(collection_ids=[collection_id], user=user)[0]

        if user.role != ROLE_LEVEL_2 and collection.type == PUBLIC_COLLECTION_TYPE:
            raise WrongCollectionTypeException()

        # delete chunks
        filter = Filter(must=[FieldCondition(key="metadata.document_id", match=MatchAny(any=[document_id]))])
        super().delete(collection_name=collection.id, points_selector=FilterSelector(filter=filter))

        # delete document
        super().delete(collection_name=self.DOCUMENT_COLLECTION_ID, points_selector=PointIdsList(points=[document_id]))

    def _build_index(self, collection_ids: List[str] | str, user: User) -> str:
        if isinstance(collection_ids, str):
            collection_ids = [collection_ids]
        return "-".join(collection_ids + [user.id])

    def _build_query_filter(self, prompt: str):
        fuzziness = {}
        if len(prompt.split()) < 25:
            fuzziness = {"fuzziness": "AUTO"}
        return {"multi_match": {"query": prompt, "type": "best_fields", "tie_breaker": 0.3, **fuzziness}}

    def _build_lexical_query_body(self, prompt: str, limit: int) -> dict:
        return {
            "query": self._build_query_filter(prompt),
            "size": int(limit * self.hybrid_limit_factor),
            "_source": {"excludes": ["embedding"]},
        }

    def _build_semantic_query_body(self, prompt: str, embedding: list[float], limit: int) -> dict:
        return {
            "knn": {
                "field": "embedding",
                "query_vector": embedding,
                "k": int(limit * self.hybrid_limit_factor),
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
