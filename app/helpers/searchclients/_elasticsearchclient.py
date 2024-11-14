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
from app.schemas.search import Filter, Search
from app.utils.exceptions import (
    DifferentCollectionsModelsException,
    WrongCollectionTypeException,
    WrongModelTypeException,
    CollectionNotFoundException,
)
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
    BATCH_SIZE = 48

    def __init__(self, models: List[str] = None, hybrid_limit_factor: float = 1.5, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert super().ping(), "Elasticsearch is not reachable"
        self.models = models
        self.hybrid_limit_factor = hybrid_limit_factor

    def upsert(self, chunks: List[Chunk], collection_id: str, user: Optional[User] = None) -> None:
        collection = self.get_collections(collection_ids=[collection_id], user=user)[0]

        if user.role != ROLE_LEVEL_2 and collection.type == PUBLIC_COLLECTION_TYPE:
            raise WrongCollectionTypeException()

        for i in range(0, len(chunks), self.BATCH_SIZE):
            batch = chunks[i : i + self.BATCH_SIZE]
            # Create mapping for metadata fields to use keyword type
            actions = [{"_index": collection_id, "_source": {"body": chunk.content, "metadata": chunk.metadata.model_dump()}} for chunk in batch]
            helpers.bulk(self, actions, index=collection_id)

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
        if method == LEXICAL_SEARCH_TYPE:
            return self._lexical_query(prompt, collection_ids, k)
        else:
            embedding = self._create_embedding(prompt, collection_ids, user)
            if method == SEMANTIC_SEARCH_TYPE:
                return self._semantic_query(embedding, collection_ids, k)
            elif method == HYBRID_SEARCH_TYPE:
                return self._hybrid_query(embedding, collection_ids, k)
        raise ValueError(f"Invalid search method: {method}")

    def collection_exists(self, collection_id: str, user: Optional[User] = None) -> bool:
        return self.get_collections(collection_ids=[collection_id], user=user) != []

    def get_collections(self, user: Optional[User] = None, collection_ids: List[str] = []) -> List[Collection]:
        """
        See SearchClient.get_collections
        """
        index_pattern = ",".join(collection_ids)
        collections_by_id = {}

        try:
            results = self.indices.get_mapping(index=index_pattern)
        except Exception as e:
            raise CollectionNotFoundException()

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

    def create_collection(
        self, collection_id: str, collection_name: str, collection_model: str, collection_type: str, collection_description: str, user: User
    ) -> None:
        """
        See SearchClient.create_collection
        """
        if self.models[collection_model].type != EMBEDDINGS_MODEL_TYPE:
            raise WrongModelTypeException()

        if user.role != ROLE_LEVEL_2 and collection_type == PUBLIC_COLLECTION_TYPE:
            raise WrongCollectionTypeException()

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

        dims = self.models[collection_model].vector_size
        print("dims", dims, flush=True)

        mappings = {
            "properties": {
                "embedding": {"type": "dense_vector", "dims": dims},
                "body": {"type": "text"},
                "metadata": {
                    "dynamic": True,
                    "properties": {
                        "document_id": {"type": "keyword"},
                        "document_name": {"type": "keyword"},
                        "document_part": {"type": "integer"},
                        "document_created_at": {"type": "date"},
                    },
                },
            },
            "_meta": {
                "name": collection_name,
                "type": collection_type,
                "model": collection_model,
                "user": user.id,
                "description": collection_description,
                "created_at": round(time.time()),
                "documents": 0,
            },
        }

        self.indices.create(index=collection_id, mappings=mappings, settings=settings, ignore=400)

    def delete_collection(self, collection_id: str, user: User) -> None:
        """
        See SearchClient.delete_collection
        """
        self.indices.delete(index=collection_id, ignore_unavailable=True)

    def get_chunks(self, collection_id: str, document_id: str, user: User, limit: int = 10000, offset: int = 0) -> List[Chunk]:
        """
        See SearchClient.get_chunks
        """
        body = {"query": {"match": {"metadata.document_id": document_id}}, "_source": ["body", "metadata"]}
        results = self.search(index=collection_id, body=body, from_=offset, size=limit)

        chunks = []
        for hit in results["hits"]["hits"]:
            source = hit["_source"]
            chunks.append(Chunk(id=hit["_id"], content=source["body"], metadata=source["metadata"] | {"collection_id": collection_id}))

        return chunks

    # @TODO: pagination between qdrant and elasticsearch diverging
    # @TODO: offset is not supported by elasticsearch
    def get_documents(self, collection_id: str, user: Optional[User] = None, limit: int = 10000, offset: int = 0) -> List[Document]:
        """
        See SearchClient.get_documents
        """
        self.get_collections(collection_ids=[collection_id], user=user)  # check if collection exists

        body = {
            "query": {"match_all": {}},
            "_source": ["metadata"],
            "aggs": {"document_ids": {"terms": {"field": "metadata.document_id", "size": limit}}},
        }
        results = self.search(index=collection_id, body=body, size=1, from_=0)

        documents = []

        for bucket in results["aggregations"]["document_ids"]["buckets"]:
            document_id = bucket["key"]
            chunks = bucket["doc_count"]
            # retrieve only one document by document_id metadata field
            result = self.search(index=collection_id, body={"query": {"match": {"metadata.document_id": document_id}}}, size=1, from_=0)
            metadata = result["hits"]["hits"][0]["_source"]["metadata"]
            documents.append(
                Document(id=document_id, name=metadata.get("document_name"), created_at=metadata.get("document_created_at"), chunks=chunks)
            )

        return documents

    def delete_document(self, collection_id: str, document_id: str, user: Optional[User] = None):
        """
        See SearchClient.delete_document
        """
        collection = self.get_collections(collection_ids=[collection_id], user=user)[0]

        if user.role != ROLE_LEVEL_2 and collection.type == PUBLIC_COLLECTION_TYPE:
            raise WrongCollectionTypeException()

        # delete chunks
        body = {"query": {"match": {"metadata.document_id": document_id}}}
        self.delete_by_query(index=collection_id, body=body)

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

    def _lexical_query(self, prompt: str, collection_ids: List[str], size: int = 4) -> List[Search]:
        body = {"query": self._build_query_filter(prompt), "size": size}
        results = self.search(index=",".join(collection_ids), body=body)
        hits = [x.get("_source") for x in results["hits"]["hits"] if x]
        searches = hits
        return searches

    def _hybrid_query(self, prompt: str, embedding: list[float], collection_ids: List[str], limit: int = 4) -> List[Search]:
        # See also: https://elasticsearch-py.readthedocs.io/en/v8.14.0/async.html
        with ThreadPoolExecutor(max_workers=2) as executor:
            lexical_query_body = self._build_lexical_query_body(prompt, limit)
            semantic_query_body = self._build_semantic_query_body(prompt, embedding, limit)
            lexical_future = executor.submit(self.search, ",".join(collection_ids), lexical_query_body)
            semantic_future = executor.submit(self.search, ",".join(collection_ids), semantic_query_body)
            lexical_hits = [x for x in lexical_future.result()["hits"]["hits"] if x]
            semantic_hits = [x for x in semantic_future.result()["hits"]["hits"] if x]

        results = self._rrf_ranker([lexical_hits, semantic_hits], limit=limit)
        hits = [x.get("_source") for x in results]
        return hits

    def _semantic_query(self, prompt: str, embedding: list[float], collection_ids: List[str], limit: int) -> List[Search]:
        # See also: https://elasticsearch-py.readthedocs.io/en/v8.14.0/async.html
        with ThreadPoolExecutor(max_workers=2) as executor:
            semantic_query_body = self._build_semantic_query_body(prompt, embedding, limit)
            semantic_future = executor.submit(self.search, ",".join(collection_ids), semantic_query_body)
            semantic_hits = [x for x in semantic_future.result()["hits"]["hits"] if x]

        results = self._rrf_ranker([semantic_hits], limit=limit)
        hits = [x.get("_source") for x in results]
        return hits

    # @TODO: support multiple input in same time
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
