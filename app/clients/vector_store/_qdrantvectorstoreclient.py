import logging
from typing import List, Optional
from uuid import uuid4

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    IntegerIndexType,
    MatchAny,
    MatchValue,
    OrderBy,
    PointStruct,
    VectorParams,
)

from app.schemas.chunks import Chunk
from app.schemas.search import Search, SearchMethod
from app.utils.exceptions import NotImplementedException

from app.clients.vector_store._basevectorstoreclient import BaseVectorStoreClient

logger = logging.getLogger(__name__)


class QdrantVectorStoreClient(BaseVectorStoreClient, AsyncQdrantClient):
    default_method = SearchMethod.SEMANTIC

    def __init__(self, *args, model = None, **kwargs):
        BaseVectorStoreClient.__init__(self, *args, model=model, **kwargs)
        AsyncQdrantClient.__init__(self, *args, **kwargs)
        self.url = kwargs.get("url")

    async def check(self) -> bool:
        try:
            await AsyncQdrantClient.collection_exists(self, collection_name="test")  # raise error only if connection is not established
            return True
        except Exception as e:
            logger.exception("Qdrant client check failed: %s", e)
            return False

    async def close(self):
        await AsyncQdrantClient.close(self)

    async def create_collection(self, collection_id: int, vector_size: int) -> None:
        await AsyncQdrantClient.create_collection(
            self,
            collection_name=str(collection_id),
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        await self.create_payload_index(collection_name=str(collection_id), field_name="id", field_schema=IntegerIndexType.INTEGER)

    async def delete_collection(self, collection_id: int) -> None:
        await AsyncQdrantClient.delete_collection(self, collection_name=str(collection_id))

    async def get_collections(self) -> list[int]:
        collections = await AsyncQdrantClient.get_collections(self)
        return [int(collection.name) for collection in collections.collections]

    async def get_chunk_count(self, collection_id: int, document_id: int) -> Optional[int]:
        try:
            chunks_count = await AsyncQdrantClient.count(
                self,
                collection_name=str(collection_id),
                count_filter=Filter(must=[FieldCondition(key="metadata.document_id", match=MatchAny(any=[document_id]))]),
            )
            return chunks_count.count
        except ResponseHandlingException as e:
            return None

    async def delete_document(self, collection_id: int, document_id: int) -> None:
        doc_filter = Filter(must=[FieldCondition(key="metadata.document_id", match=MatchAny(any=[document_id]))])
        await AsyncQdrantClient.delete(self, collection_name=str(collection_id), points_selector=FilterSelector(filter=doc_filter))

    async def get_chunks(self, collection_id: int, document_id: int, offset: int = 0, limit: int = 10, chunk_id: Optional[int] = None) -> List[Chunk]:
        must = [FieldCondition(key="metadata.document_id", match=MatchAny(any=[document_id]))]
        if chunk_id:
            must.append(FieldCondition(key="metadata.id", match=MatchValue(value=chunk_id)))

        doc_filter = Filter(must=must)
        data = await AsyncQdrantClient.scroll(
            self,
            collection_name=str(collection_id),
            scroll_filter=doc_filter,
            order_by=OrderBy(key="id", start_from=offset),
            limit=limit,
        )
        data = data[0]
        chunks = [Chunk(id=chunk.payload["id"], content=chunk.payload["content"], metadata=chunk.payload["metadata"]) for chunk in data]

        return chunks

    async def upsert(self, collection_id: int, chunks: List[Chunk], embeddings: List[list[float]]) -> None:
        await AsyncQdrantClient.upsert(
            self,
            collection_name=str(collection_id),
            points=[
                PointStruct(id=str(uuid4()), vector=embedding, payload={"id": chunk.id, "content": chunk.content, "metadata": chunk.metadata})
                for chunk, embedding in zip(chunks, embeddings)
            ],
        )

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
        if method == SearchMethod.LEXICAL:
            searches = await self._lexical_search(query_prompt=query_prompt, collection_ids=collection_ids, k=k)

        elif method == SearchMethod.SEMANTIC:
            searches = await self._semantic_query(query_vector=query_vector, collection_ids=collection_ids, k=k, score_threshold=score_threshold)

        else:  # method == SearchMethod.HYBRID
            searches = await self._hybrid_search(query_prompt=query_prompt, query_vector=query_vector, collection_ids=collection_ids, k=k, rff_k=rff_k)  # fmt: off

        return searches

    async def _lexical_search(self, query_prompt: str, collection_ids: List[int], k: int) -> List[Search]:
        raise NotImplementedException("Only semantic search is available for Qdrant database.")

    async def _semantic_query(self, query_vector: list[float], collection_ids: List[int], k: int, score_threshold: float = 0.0) -> List[Search]:
        searches = []
        for collection_id in collection_ids:
            results = await AsyncQdrantClient.search(
                self,
                collection_name=str(collection_id),
                query_vector=query_vector,
                limit=k,
                score_threshold=score_threshold,
                with_payload=True,
            )
            searches.extend(
                Search(
                    method=SearchMethod.SEMANTIC.value,
                    score=chunk.score,
                    chunk=Chunk(id=chunk.payload["id"], content=chunk.payload["content"], metadata=chunk.payload["metadata"]),
                )
                for chunk in results
            )

        searches = [search for search in searches if search.score >= score_threshold]
        searches = sorted(searches, key=lambda x: x.score, reverse=True)[:k]

        return searches

    async def _hybrid_search(self, query_prompt: str, query_vector: list[float], collection_ids: List[int], k: int, rff_k: Optional[int] = 20) -> List[Search]:  # fmt: off
        raise NotImplementedException("Only semantic search is available for Qdrant database.")
