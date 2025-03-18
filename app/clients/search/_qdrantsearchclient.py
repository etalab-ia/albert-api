import time
from typing import List, Literal, Optional
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    HasIdCondition,
    MatchAny,
    PointIdsList,
    PointStruct,
    VectorParams,
)


from app.clients.search import BaseSearchClient
from app.helpers import ModelRegistry, IdentityAccessManager
from app.schemas.chunks import Chunk, ChunkMetadata
from app.schemas.collections import Collection
from app.schemas.documents import Document
from app.schemas.search import Search
from app.utils.exceptions import (
    CollectionNotFoundException,
    DifferentCollectionsModelsException,
    NotImplementedException,
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


class QdrantSearchClient(QdrantClient, BaseSearchClient):
    BATCH_SIZE = 48
    METADATA_COLLECTION_ID = "collections"
    DOCUMENT_COLLECTION_ID = "documents"

    def __init__(self, models: ModelRegistry, auth: IdentityAccessManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.models = models
        self.auth = auth
        if not super().collection_exists(collection_name=self.METADATA_COLLECTION_ID):
            super().create_collection(collection_name=self.METADATA_COLLECTION_ID, vectors_config={}, on_disk_payload=False)

        if not super().collection_exists(collection_name=self.DOCUMENT_COLLECTION_ID):
            super().create_collection(collection_name=self.DOCUMENT_COLLECTION_ID, vectors_config={}, on_disk_payload=False)

    async def upsert(self, chunks: List[Chunk], collection_id: str, user_id: str) -> None:
        """
        See SearchClient.upsert
        """
        collection = self.get_collections(collection_ids=[collection_id], user_id=user_id)[0]

        for i in range(0, len(chunks), self.BATCH_SIZE):
            batch = chunks[i : i + self.BATCH_SIZE]

            # create a document point for GET /v1/documents endpoint
            super().upsert(
                collection_name=self.DOCUMENT_COLLECTION_ID,
                points=[
                    PointStruct(
                        id=chunk.metadata.document_id,
                        vector={},
                        payload={
                            "collection_id": collection_id,
                            "name": chunk.metadata.document_name,
                            "created_at": chunk.metadata.document_created_at,
                        },
                    )
                    for chunk in batch
                ],
            )

            # create embeddings
            texts = [chunk.content for chunk in batch]
            embeddings = await self._create_embeddings(input=texts, model=collection.model)

            # insert chunks and vectors
            super().upsert(
                collection_name=collection_id,
                points=[
                    PointStruct(id=chunk.id, vector=embedding, payload={"content": chunk.content, "metadata": chunk.metadata.model_dump()})
                    for chunk, embedding in zip(batch, embeddings)
                ],
            )

        # update collection documents count
        payload = collection.model_dump()
        payload["documents"] = (
            super()
            .count(
                collection_name=self.DOCUMENT_COLLECTION_ID,
                count_filter=Filter(must=[FieldCondition(key="collection_id", match=MatchAny(any=[collection.id]))]),
            )
            .count
        )
        payload.pop("id")
        super().upsert(collection_name=self.METADATA_COLLECTION_ID, points=[PointStruct(id=collection.id, payload=payload, vector={})])

    async def query(
        self,
        prompt: str,
        user_id: str,
        collection_ids: List[str] = [],
        method: Literal[SEARCH_TYPE__HYBRID, SEARCH_TYPE__LEXICAL, SEARCH_TYPE__SEMANTIC] = SEARCH_TYPE__SEMANTIC,
        k: Optional[int] = 4,
        rff_k: Optional[int] = 20,
        score_threshold: Optional[float] = None,
    ) -> List[Search]:
        """
        See SearchClient.query
        """

        if method != SEARCH_TYPE__SEMANTIC:
            raise NotImplementedException("Lexical and hybrid search are not available for Qdrant database.")

        collections = self.get_collections(collection_ids=collection_ids, user_id=user_id)

        if len(set(collection.model for collection in collections)) > 1:
            raise DifferentCollectionsModelsException()

        response = await self._create_embeddings(input=[prompt], model=collections[0].model)

        chunks = []
        for collection in collections:
            results = super().search(
                collection_name=collection.id,
                query_vector=response[0],
                limit=k,
                score_threshold=score_threshold,
                with_payload=True,
            )
            for result in results:
                result.payload["metadata"]["collection"] = collection.id
            chunks.extend(results)

        # sort by similarity score and get top k
        chunks = sorted(chunks, key=lambda x: x.score, reverse=True)[:k]
        searches = [
            Search(method=method, score=chunk.score, chunk=Chunk(id=chunk.id, content=chunk.payload["content"], metadata=chunk.payload["metadata"]))
            for chunk in chunks
        ]

        return searches

    def get_collections(self, user_id: str, collection_ids: List[str] = []) -> List[Collection]:
        """
        See SearchClient.get_collections
        """
        # if no collection ids are provided, get all collections
        must = [HasIdCondition(has_id=collection_ids)] if collection_ids else []

        should = []
        if user_id:
            should.append(FieldCondition(key="user", match=MatchAny(any=[user_id])))
        should.append(FieldCondition(key="type", match=MatchAny(any=[COLLECTION_TYPE__PUBLIC])))
        filter = Filter(must=must, should=should)

        records = super().scroll(collection_name=self.METADATA_COLLECTION_ID, scroll_filter=filter, limit=1000, offset=None)
        data, offset = records[0], records[1]
        while offset is not None:
            records = super().scroll(collection_name=self.METADATA_COLLECTION_ID, scroll_filter=filter, limit=1000, offset=offset)
            data.extend(records[0])
            offset = records[1]

        # sanity check: remove collection that does not exist
        existing_collection_ids = [collection.name for collection in super().get_collections().collections]
        data = [collection for collection in data if collection.id in existing_collection_ids]

        # check if collection ids are valid
        existing_collection_ids = [collection.id for collection in data]
        for collection_id in collection_ids:
            if collection_id not in existing_collection_ids:
                raise CollectionNotFoundException()

        collections = list()
        for collection in data:
            collections.append(
                Collection(
                    id=collection.id,
                    name=collection.payload.get("name"),
                    type=collection.payload.get("type"),
                    model=collection.payload.get("model"),
                    description=collection.payload.get("description"),
                    created_at=collection.payload.get("created_at"),
                    documents=collection.payload.get("documents"),
                )
            )

        return collections

    async def create_collection(
        self,
        collection_id: str,
        collection_name: str,
        collection_model: str,
        user_id: str,
        collection_type: str = COLLECTION_TYPE__PRIVATE,
        collection_description: Optional[str] = None,
    ) -> Collection:
        """
        See SearchClient.create_collection
        """

        model = self.models(model=collection_model)
        if model.type != MODEL_TYPE__EMBEDDINGS:
            raise WrongModelTypeException()

        # create metadata
        metadata = {
            "name": collection_name,
            "type": collection_type,
            "model": collection_model,
            "user": user_id,
            "description": collection_description,
            "created_at": round(time.time()),
            "documents": 0,
        }
        super().upsert(collection_name=self.METADATA_COLLECTION_ID, points=[PointStruct(id=collection_id, payload=dict(metadata), vector={})])

        super().create_collection(collection_name=collection_id, vectors_config=VectorParams(size=model._vector_size, distance=Distance.COSINE))

        return Collection(id=collection_id, **metadata)

    async def delete_collection(self, collection_id: str, user_id) -> None:
        """
        See SearchClient.delete_collection
        """
        collection = self.get_collections(collection_ids=[collection_id], user_id=user_id)[0]

        super().delete_collection(collection_name=collection.id)
        super().delete(collection_name=self.METADATA_COLLECTION_ID, points_selector=PointIdsList(points=[collection.id]))

    def get_chunks(self, collection_id: str, document_id: str, user_id: str, limit: int = 10, offset: Optional[UUID] = None) -> List[Chunk]:
        """
        See SearchClient.get_chunks
        """
        collection = self.get_collections(collection_ids=[collection_id], user_id=user_id)[0]

        filter = Filter(must=[FieldCondition(key="metadata.document_id", match=MatchAny(any=[document_id]))])
        data = super().scroll(collection_name=collection.id, scroll_filter=filter, limit=limit, offset=offset)[0]
        chunks = [Chunk(id=chunk.id, content=chunk.payload["content"], metadata=ChunkMetadata(**chunk.payload["metadata"])) for chunk in data]

        return chunks

    def get_documents(self, collection_id: str, user_id: str, limit: int = 10, offset: Optional[UUID] = None) -> List[Document]:
        """
        See SearchClient.get_documents
        """
        collection = self.get_collections(collection_ids=[collection_id], user_id=user_id)[0]

        filter = Filter(must=[FieldCondition(key="collection_id", match=MatchAny(any=[collection_id]))])
        data = super().scroll(collection_name=self.DOCUMENT_COLLECTION_ID, scroll_filter=filter, limit=limit, offset=offset)[0]
        documents = list()
        for document in data:
            try:
                chunks_count = (
                    super()
                    .count(
                        collection_name=collection.id,
                        count_filter=Filter(must=[FieldCondition(key="metadata.document_id", match=MatchAny(any=[document.id]))]),
                    )
                    .count
                )
            except ResponseHandlingException as e:
                chunks_count = None
            documents.append(Document(id=document.id, name=document.payload["name"], created_at=document.payload["created_at"], chunks=chunks_count))

        return documents

    async def delete_document(self, collection_id: str, document_id: str, user_id: str):
        """
        See SearchClient.delete_document
        """
        collection = self.get_collections(collection_ids=[collection_id], user_id=user_id)[0]

        # delete chunks
        filter = Filter(must=[FieldCondition(key="metadata.document_id", match=MatchAny(any=[document_id]))])
        super().delete(collection_name=collection.id, points_selector=FilterSelector(filter=filter))

        # delete document
        super().delete(collection_name=self.DOCUMENT_COLLECTION_ID, points_selector=PointIdsList(points=[document_id]))
