import time
from typing import List, Literal, Optional

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

from app.helpers.searchclients._searchclient import SearchClient
from app.schemas.chunks import Chunk, ChunkMetadata
from app.schemas.collections import Collection
from app.schemas.documents import Document
from app.schemas.search import Search
from app.schemas.security import Role
from app.schemas.security import User
from app.utils.exceptions import (
    CollectionNotFoundException,
    DifferentCollectionsModelsException,
    NotImplementedException,
    WrongModelTypeException,
    InsufficientRightsException,
)
from app.utils.variables import (
    EMBEDDINGS_MODEL_TYPE,
    LEXICAL_SEARCH_TYPE,
    HYBRID_SEARCH_TYPE,
    PUBLIC_COLLECTION_TYPE,
    SEMANTIC_SEARCH_TYPE,
    PRIVATE_COLLECTION_TYPE,
)


class QdrantSearchClient(QdrantClient, SearchClient):
    BATCH_SIZE = 48
    METADATA_COLLECTION_ID = "collections"
    DOCUMENT_COLLECTION_ID = "documents"

    def __init__(self, models, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.models = models

        if not super().collection_exists(collection_name=self.METADATA_COLLECTION_ID):
            super().create_collection(collection_name=self.METADATA_COLLECTION_ID, vectors_config={}, on_disk_payload=False)

        if not super().collection_exists(collection_name=self.DOCUMENT_COLLECTION_ID):
            super().create_collection(collection_name=self.DOCUMENT_COLLECTION_ID, vectors_config={}, on_disk_payload=False)

    def upsert(self, chunks: List[Chunk], collection_id: str, user: User) -> None:
        """
        See SearchClient.upsert
        """
        collection = self.get_collections(collection_ids=[collection_id], user=user)[0]

        if user.role != Role.ADMIN and collection.type == PUBLIC_COLLECTION_TYPE:
            raise InsufficientRightsException()

        for i in range(0, len(chunks), self.BATCH_SIZE):
            batch = chunks[i : i + self.BATCH_SIZE]

            # insert documents
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
            response = self.models[collection.model].embeddings.create(input=texts, model=collection.model)
            vectors = [vector.embedding for vector in response.data]

            # insert chunks and vectors
            super().upsert(
                collection_name=collection_id,
                points=[
                    PointStruct(id=chunk.id, vector=vector, payload={"content": chunk.content, "metadata": chunk.metadata.model_dump()})
                    for chunk, vector in zip(batch, vectors)
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

    def query(
        self,
        prompt: str,
        user: User,
        collection_ids: List[str] = [],
        method: Literal[HYBRID_SEARCH_TYPE, LEXICAL_SEARCH_TYPE, SEMANTIC_SEARCH_TYPE] = SEMANTIC_SEARCH_TYPE,
        k: Optional[int] = 4,
        rff_k: Optional[int] = 20,
        score_threshold: Optional[float] = None,
    ) -> List[Search]:
        """
        See SearchClient.query
        """

        if method != SEMANTIC_SEARCH_TYPE:
            raise NotImplementedException("Lexical and hybrid search are not available for Qdrant database.")

        collections = self.get_collections(collection_ids=collection_ids, user=user)
        if len(set(collection.model for collection in collections)) > 1:
            raise DifferentCollectionsModelsException()

        model = collections[0].model
        response = self.models[model].embeddings.create(input=[prompt], model=model)
        vector = response.data[0].embedding

        chunks = []
        for collection in collections:
            results = super().search(
                collection_name=collection.id,
                query_vector=vector,
                limit=k,
                score_threshold=score_threshold,
                with_payload=True,
            )
            for result in results:
                result.payload["metadata"]["collection"] = collection.id
            chunks.extend(results)

        # sort by similarity score and get top k
        chunks = sorted(chunks, key=lambda x: x.score, reverse=True)[:k]
        results = [
            Search(method=method, score=chunk.score, chunk=Chunk(id=chunk.id, content=chunk.payload["content"], metadata=chunk.payload["metadata"]))
            for chunk in chunks
        ]

        return results

    def get_collections(
        self,
        user: User,
        collection_ids: List[str] = [],
    ) -> List[Collection]:
        """
        See SearchClient.get_collections
        """
        # if no collection ids are provided, get all collections
        must = [HasIdCondition(has_id=collection_ids)] if collection_ids else []
        should = []
        if user:
            should.append(FieldCondition(key="user", match=MatchAny(any=[user.id])))
        should.append(FieldCondition(key="type", match=MatchAny(any=[PUBLIC_COLLECTION_TYPE])))

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
                    user=collection.payload.get("user"),
                    description=collection.payload.get("description"),
                    created_at=collection.payload.get("created_at"),
                    documents=collection.payload.get("documents"),
                )
            )

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

        if user.role != Role.ADMIN and collection_type == PUBLIC_COLLECTION_TYPE:
            raise InsufficientRightsException()

        # create metadata
        metadata = {
            "name": collection_name,
            "type": collection_type,
            "model": collection_model,
            "user": user.id,
            "description": collection_description,
            "created_at": round(time.time()),
            "documents": 0,
        }
        super().upsert(collection_name=self.METADATA_COLLECTION_ID, points=[PointStruct(id=collection_id, payload=dict(metadata), vector={})])

        super().create_collection(
            collection_name=collection_id, vectors_config=VectorParams(size=self.models[collection_model].vector_size, distance=Distance.COSINE)
        )

        return Collection(id=collection_id, **metadata)

    def delete_collection(self, collection_id: str, user: User) -> None:
        """
        See SearchClient.delete_collection
        """
        collection = self.get_collections(collection_ids=[collection_id], user=user)[0]

        if user.role != Role.ADMIN and collection.type == PUBLIC_COLLECTION_TYPE:
            raise InsufficientRightsException()

        super().delete_collection(collection_name=collection.id)
        super().delete(collection_name=self.METADATA_COLLECTION_ID, points_selector=PointIdsList(points=[collection.id]))

    def get_chunks(self, collection_id: str, document_id: str, user: User, limit: Optional[int] = 10, offset: Optional[int] = None) -> List[Chunk]:
        """
        See SearchClient.get_chunks
        """
        collection = self.get_collections(collection_ids=[collection_id], user=user)[0]

        filter = Filter(must=[FieldCondition(key="metadata.document_id", match=MatchAny(any=[document_id]))])
        data = super().scroll(collection_name=collection.id, scroll_filter=filter, limit=limit, offset=offset)[0]
        chunks = [Chunk(id=chunk.id, content=chunk.payload["content"], metadata=ChunkMetadata(**chunk.payload["metadata"])) for chunk in data]

        return chunks

    def get_documents(self, collection_id: str, user: User, limit: Optional[int] = 10, offset: Optional[int] = None) -> List[Document]:
        """
        See SearchClient.get_documents
        """
        collection = self.get_collections(collection_ids=[collection_id], user=user)[0]

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

    def delete_document(self, collection_id: str, document_id: str, user: User):
        """
        See SearchClient.delete_document
        """
        collection = self.get_collections(collection_ids=[collection_id], user=user)[0]

        if user.role != Role.ADMIN and collection.type == PUBLIC_COLLECTION_TYPE:
            raise InsufficientRightsException()

        # delete chunks
        filter = Filter(must=[FieldCondition(key="metadata.document_id", match=MatchAny(any=[document_id]))])
        super().delete(collection_name=collection.id, points_selector=FilterSelector(filter=filter))

        # delete document
        super().delete(collection_name=self.DOCUMENT_COLLECTION_ID, points_selector=PointIdsList(points=[document_id]))
