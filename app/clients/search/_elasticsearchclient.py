from concurrent.futures import ThreadPoolExecutor
import time
from typing import List, Literal, Optional

from elasticsearch import Elasticsearch, NotFoundError, helpers

from app.clients.search import BaseSearchClient
from app.helpers import ModelRegistry
from app.schemas.chunks import Chunk, ChunkMetadata
from app.schemas.collections import Collection
from app.schemas.documents import Document
from app.schemas.search import Search
from app.schemas.security import Role, User
from app.utils.exceptions import (
    CollectionNotFoundException,
    DifferentCollectionsModelsException,
    InsufficientRightsException,
    WrongModelTypeException,
)
from app.utils.variables import (
    COLLECTION_TYPE__PRIVATE,
    COLLECTION_TYPE__PUBLIC,
    MODEL_TYPE__EMBEDDINGS,
    SEARCH_TYPE__HYBRID,
    SEARCH_TYPE__LEXICAL,
    SEARCH_TYPE__SEMANTIC,
)


class ElasticSearchClient(Elasticsearch, BaseSearchClient):
    BATCH_SIZE = 48

    def __init__(self, models: ModelRegistry, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert super().ping(), "Elasticsearch is not reachable"
        self.models = models

    async def upsert(self, chunks: List[Chunk], collection_id: str, user: User) -> None:
        """
        See SearchClient.upsert
        """
        collection = self.get_collections(collection_ids=[collection_id], user=user)[0]

        if user.role != Role.ADMIN and collection.type == COLLECTION_TYPE__PUBLIC:
            raise InsufficientRightsException()

        for i in range(0, len(chunks), self.BATCH_SIZE):
            batch = chunks[i : i + self.BATCH_SIZE]

            # create embeddings
            texts = [chunk.content for chunk in batch]
            embeddings = await self._create_embeddings(input=texts, model=collection.model)

            # insert chunks and vectors
            actions = [
                {
                    "_index": collection_id,
                    "_source": {
                        "body": chunk.content,
                        "embedding": embedding,
                        "metadata": chunk.metadata.model_dump(),
                    },
                }
                for chunk, embedding in zip(batch, embeddings)
            ]
            helpers.bulk(self, actions, index=collection_id)
        # update collection documents count
        self.indices.refresh(index=collection_id)

    async def query(
        self,
        prompt: str,
        user: User,
        collection_ids: List[str] = [],
        method: Literal[SEARCH_TYPE__HYBRID, SEARCH_TYPE__LEXICAL, SEARCH_TYPE__SEMANTIC] = SEARCH_TYPE__SEMANTIC,
        k: Optional[int] = 4,
        rff_k: Optional[int] = 20,
    ) -> List[Search]:
        """
        See SearchClient.query
        """
        collections = self.get_collections(collection_ids=collection_ids, user=user)

        if method == SEARCH_TYPE__LEXICAL:
            searches = self._lexical_query(prompt=prompt, collection_ids=collection_ids, k=k)

            return searches

        if len(set(collection.model for collection in collections)) > 1:
            raise DifferentCollectionsModelsException()

        embedding = await self._create_embeddings(input=[prompt], model=collections[0].model)[0]

        if method == SEARCH_TYPE__SEMANTIC:
            searches = self._semantic_query(prompt=prompt, embedding=embedding, collection_ids=collection_ids, size=k)

            return searches

        if method == SEARCH_TYPE__HYBRID:
            with ThreadPoolExecutor(max_workers=2) as executor:
                lexical_searches = executor.submit(self._lexical_query, prompt, collection_ids, k).result()
                semantic_searches = executor.submit(self._semantic_query, prompt, embedding, collection_ids, k).result()
                searches = self.build_ranked_searches(searches_list=[lexical_searches, semantic_searches], k=k, rff_k=rff_k)

        return searches

    def get_collections(self, user: User, collection_ids: List[str] = []) -> List[Collection]:
        """
        See SearchClient.get_collections
        """
        # if no collection ids are provided, get all collections
        index_pattern = ",".join(collection_ids) if collection_ids else "*"

        try:
            collections = [
                Collection(id=collection_id, **metadata["mappings"]["_meta"])
                for collection_id, metadata in self.indices.get(index=index_pattern, filter_path=["*.mappings._meta"]).items()
            ]
        except NotFoundError as e:
            raise CollectionNotFoundException()

        collections = [collection for collection in collections if collection.user == user.id or collection.type == COLLECTION_TYPE__PUBLIC]

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
        collection_type: str = COLLECTION_TYPE__PRIVATE,
        collection_description: Optional[str] = None,
    ) -> Collection:
        """
        See SearchClient.create_collection
        """
        model = self.models[collection_model]
        if model.type != MODEL_TYPE__EMBEDDINGS:
            raise WrongModelTypeException()

        if user.role != Role.ADMIN and collection_type == COLLECTION_TYPE__PUBLIC:
            raise InsufficientRightsException()

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
                "embedding": {"type": "dense_vector", "dims": model._vector_size},
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
        collection = self.get_collections(collection_ids=[collection_id], user=user)[0]

        if user.role != Role.ADMIN and collection.type == COLLECTION_TYPE__PUBLIC:
            raise InsufficientRightsException()

        self.indices.delete(index=collection_id, ignore_unavailable=True)

    def get_chunks(self, collection_id: str, document_id: str, user: User, limit: int = 10, offset: int = 0) -> List[Chunk]:
        """
        See SearchClient.get_chunks
        """
        collection = self.get_collections(collection_ids=[collection_id], user=user)[0]

        body = {"query": {"match": {"metadata.document_id": document_id}}, "_source": ["body", "metadata"]}
        results = self.search(index=collection.id, body=body, from_=offset, size=limit)

        chunks = []
        for hit in results["hits"]["hits"]:
            source = hit["_source"]
            metadata = source["metadata"] | {"collection_id": collection_id}
            chunks.append(Chunk(id=hit["_id"], content=source["body"], metadata=ChunkMetadata(**metadata)))

        return chunks

    # @TODO: pagination between qdrant and elasticsearch diverging
    # @TODO: offset is not supported by elasticsearch
    def get_documents(self, collection_id: str, user: User, limit: int = 10, offset: int = 0) -> List[Document]:
        """
        See SearchClient.get_documents
        """
        _ = self.get_collections(collection_ids=[collection_id], user=user)  # check if collection exists

        body = {
            "query": {"match_all": {}},
            "_source": ["metadata"],
            "aggs": {"document_ids": {"terms": {"field": "metadata.document_id", "size": limit}}},
        }
        results = self.search(index=collection_id, body=body, from_=0, size=limit)

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

    def delete_document(self, collection_id: str, document_id: str, user: User):
        """
        See SearchClient.delete_document
        """
        collection = self.get_collections(collection_ids=[collection_id], user=user)[0]

        if user.role != Role.ADMIN and collection.type == COLLECTION_TYPE__PUBLIC:
            raise InsufficientRightsException()

        # delete chunks
        body = {"query": {"match": {"metadata.document_id": document_id}}}
        self.delete_by_query(index=collection_id, body=body)
        self.indices.refresh(index=collection_id)

    def _build_query_filter(self, prompt: str):
        fuzziness = {}
        if len(prompt.split()) < 25:
            fuzziness = {"fuzziness": "AUTO"}
        return {"multi_match": {"query": prompt, **fuzziness}}

    def _build_search(self, hit: dict) -> Search:
        return Search(
            score=hit["_score"],
            chunk=Chunk(
                id=hit["_id"],
                content=hit["_source"]["body"],
                metadata=hit["_source"]["metadata"],
            ),
        )

    def _lexical_query(self, prompt: str, collection_ids: List[str], size: int) -> List[Search]:
        body = {
            "query": self._build_query_filter(prompt=prompt),
            "size": size,
            "_source": {"excludes": ["embedding"]},
        }
        results = self.search(index=",".join(collection_ids), body=body)
        hits = [hit for hit in results["hits"]["hits"] if hit]
        return [self._build_search(hit=hit) for hit in hits]

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
        return [self._build_search(hit) for hit in hits]

    @staticmethod
    def build_ranked_searches(searches_list: List[List[Search]], k: int, rff_k: Optional[int] = 20) -> List[Search]:
        """
        Combine search results using Reciprocal Rank Fusion (RRF)

        Args:
            searches_list (List[List[Search]]): A list of searches from different query
            k (int): The number of results to return
            rff_k (Optional[int]): The constant k in the RRF formula

        Returns:
            A combined list of searches with updated scores
        """

        combined_scores = {}
        search_map = {}
        for searches in searches_list:
            for rank, search in enumerate(searches):
                chunk_id = search.chunk.id
                if chunk_id not in combined_scores:
                    combined_scores[chunk_id] = 0
                    search_map[chunk_id] = search
                else:
                    search_map[chunk_id].method = search_map[chunk_id].method + "/" + search.method
                combined_scores[chunk_id] += 1 / (rff_k + rank + 1)

        ranked_scores = sorted(combined_scores.items(), key=lambda item: item[1], reverse=True)
        reranked_searches = []
        for chunk_id, rrf_score in ranked_scores:
            search = search_map[chunk_id]
            search.score = rrf_score
            reranked_searches.append(search)

        if k:
            return reranked_searches[:k]
        return reranked_searches
