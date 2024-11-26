from typing import List, Literal, Optional
import functools
import time
from concurrent.futures import ThreadPoolExecutor

from elasticsearch import Elasticsearch, helpers, NotFoundError

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
    SearchMethodNotAvailableException,
)
from app.utils.variables import (
    EMBEDDINGS_MODEL_TYPE,
    HYBRID_SEARCH_TYPE,
    LEXICAL_SEARCH_TYPE,
    SEMANTIC_SEARCH_TYPE,
    ROLE_LEVEL_2,
    PUBLIC_COLLECTION_TYPE,
    PRIVATE_COLLECTION_TYPE,
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
            batched_chunks = chunks[i : i + self.BATCH_SIZE]
            actions = [
                {
                    "_index": collection_id,
                    "_source": {
                        "body": chunk.content,
                        "embedding": self._create_embedding(chunk.content, [collection_id], user),
                        "metadata": chunk.metadata.model_dump(),
                    },
                }
                for chunk in batched_chunks
            ]
            helpers.bulk(self, actions, index=collection_id)
        self.indices.refresh(index=collection_id)

    def query(
        self,
        prompt: str,
        user: User,
        collection_ids: List[str] = [],
        method: Literal[HYBRID_SEARCH_TYPE, LEXICAL_SEARCH_TYPE, SEMANTIC_SEARCH_TYPE] = SEMANTIC_SEARCH_TYPE,
        k: Optional[int] = 4,
        rff_k: Optional[int] = 20,
        score_threshold: Optional[float] = None,  # TODO: implement score_threshold
        filter: Optional[Filter] = None,  # TODO: implement filter
    ) -> List[Search]:
        print("SEARCH", collection_ids, flush=True)
        collections = self.get_collections(collection_ids=collection_ids, user=user)

        print("OOOO", flush=True)

        if len(set(collection.model for collection in collections)) > 1:
            raise DifferentCollectionsModelsException()

        if method == LEXICAL_SEARCH_TYPE:
            return self._lexical_query(prompt, collection_ids, k)
        elif method == SEMANTIC_SEARCH_TYPE:
            embedding = self._create_embedding(prompt, collection_ids, user)
            return self._semantic_query(prompt, embedding, collection_ids, k)
        elif method == HYBRID_SEARCH_TYPE:
            embedding = self._create_embedding(prompt, collection_ids, user)
            with ThreadPoolExecutor(max_workers=2) as executor:
                lexical_searches = executor.submit(self._lexical_query, prompt, collection_ids, k).result()
                semantic_searches = executor.submit(self._semantic_query, prompt, embedding, collection_ids, k).result()
                return self.build_ranked_searches([lexical_searches, semantic_searches], k, rff_k)
        raise SearchMethodNotAvailableException()

    def get_collections(self, collection_ids: List[str] = [], user: Optional[User] = None) -> List[Collection]:
        """
        See SearchClient.get_collections
        """
        index_pattern = ",".join(collection_ids) if collection_ids else "*"

        try:
            collections = [
                Collection(id=collection_id, **metadata["mappings"]["_meta"])
                for collection_id, metadata in self.indices.get(index=index_pattern, filter_path=["*.mappings._meta"]).items()
            ]
        except NotFoundError as e:
            raise CollectionNotFoundException()

        if user:
            collections = [collection for collection in collections if collection.user == user.id or collection.type == PUBLIC_COLLECTION_TYPE]

        print(collection_ids, collections, flush=True)
        if collection_ids:
            for collection in collections:
                if collection.id not in collection_ids:
                    raise CollectionNotFoundException()

        for collection in collections:
            body = {
                "query": {"match_all": {}},
                "_source": ["metadata"],
                "aggs": {"document_ids": {"terms": {"field": "metadata.document_id", "size": 100}}},
            }

            results = self.search(index=collection.id, body=body, size=1, from_=0)
            collection.documents = len(results["aggregations"]["document_ids"]["buckets"])

        return collections

    def create_collection(
        self,
        collection_id: str,
        collection_name: str,
        collection_model: str,
        user: User,
        collection_type: str = PRIVATE_COLLECTION_TYPE,
        collection_description: Optional[str] = None,
    ) -> Collection:
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

        return Collection(id=collection_id, **mappings["_meta"])

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
        c = self.get_collections(collection_ids=[collection_id], user=user)  # check if collection exists

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
            first_hit_matching_document_id = self.search(
                index=collection_id, body={"query": {"match": {"metadata.document_id": document_id}}}, size=1, from_=0
            )["hits"]["hits"][0]
            metadata = first_hit_matching_document_id["_source"]["metadata"]
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
        return {"multi_match": {"query": prompt, **fuzziness}}

    def _build_search(self, hit: dict, method: Literal[LEXICAL_SEARCH_TYPE, SEMANTIC_SEARCH_TYPE]) -> Search:
        return Search(
            score=hit["_score"],
            chunk=Chunk(
                id=hit["_id"],
                content=hit["_source"]["body"],
                metadata=hit["_source"]["metadata"],
            ),
            method=method,
        )

    def _lexical_query(self, prompt: str, collection_ids: List[str], size: int) -> List[Search]:
        body = {
            "query": self._build_query_filter(prompt),
            "size": size,
            "_source": {"excludes": ["embedding"]},
        }
        results = self.search(index=",".join(collection_ids), body=body)
        hits = [hit for hit in results["hits"]["hits"] if hit]
        return [self._build_search(hit, method=LEXICAL_SEARCH_TYPE) for hit in hits]

    def _semantic_query(self, prompt: str, embedding: list[float], collection_ids: List[str], size: int) -> List[Search]:
        body = {
            "knn": {
                "field": "embedding",
                "query_vector": embedding,
                "k": size,
                "num_candidates": 200,
                "filter": self._build_query_filter(prompt),
            }
        }
        results = self.search(index=",".join(collection_ids), body=body)
        hits = [hit for hit in results["hits"]["hits"] if hit]
        return [self._build_search(hit, method=SEMANTIC_SEARCH_TYPE) for hit in hits]

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
        model_name = collections[0].model
        model_client = self.models[model_name]
        response = model_client.embeddings.create(input=[prompt], model=model_name)
        return response.data[0].embedding
