import time
from typing import List, Optional

from qdrant_client import QdrantClient
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

from app.schemas.chunks import Chunk, ChunkMetadata
from app.schemas.collections import Collection
from app.schemas.documents import Document
from app.schemas.search import Search
from app.schemas.security import User
from app.utils.variables import EMBEDDINGS_MODEL_TYPE, PUBLIC_COLLECTION_TYPE, ROLE_LEVEL_2
from app.utils.exceptions import (
    DifferentCollectionsModelsException,
    WrongModelTypeException,
    WrongCollectionTypeException,
    CollectionNotFoundException,
)


class VectorStore:
    BATCH_SIZE = 48
    METADATA_COLLECTION_ID = "collections"
    DOCUMENT_COLLECTION_ID = "documents"

    def __init__(self, models: dict, *args, **kwargs):
        self.qdrant = QdrantClient(*args, **kwargs)
        self.models = models

        if not self.qdrant.collection_exists(collection_name=self.METADATA_COLLECTION_ID):
            self.qdrant.create_collection(collection_name=self.METADATA_COLLECTION_ID, vectors_config={}, on_disk_payload=False)

        if not self.qdrant.collection_exists(collection_name=self.DOCUMENT_COLLECTION_ID):
            self.qdrant.create_collection(collection_name=self.DOCUMENT_COLLECTION_ID, vectors_config={}, on_disk_payload=False)

    def upsert(self, chunks: List[Chunk], collection_id: str, user: User) -> None:
        """
        Add chunks to a collection.

        Args:
            chunks (List[Chunk]): A list of chunks to add to the collection.
            collection_id (str): The id of the collection to add the chunks to.
            user (User): The user adding the chunks.
        """
        collection = self.get_collections(collection_ids=[collection_id], user=user)[0]

        if user.role != ROLE_LEVEL_2 and collection.type == PUBLIC_COLLECTION_TYPE:
            raise WrongCollectionTypeException()

        for i in range(0, len(chunks), self.BATCH_SIZE):
            batch = chunks[i : i + self.BATCH_SIZE]

            # insert documents
            self.qdrant.upsert(
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
            self.qdrant.upsert(
                collection_name=collection_id,
                points=[
                    PointStruct(id=chunk.id, vector=vector, payload={"content": chunk.content, "metadata": chunk.metadata.model_dump()})
                    for chunk, vector in zip(batch, vectors)
                ],
            )

    def search(
        self,
        prompt: str,
        user: User,
        collection_ids: List[str] = [],
        k: Optional[int] = 4,
        score_threshold: Optional[float] = None,
        filter: Optional[Filter] = None,
    ) -> List[Search]:
        """
        Search for chunks in a collection.

        Args:
            prompt (str): The prompt to search for.
            user (User): The user searching for the chunks.
            collection_ids (List[str]): The ids of the collections to search in.
            k (Optional[int]): The number of chunks to return.
            score_threshold (Optional[float]): The score threshold for the chunks to return.
            filter (Optional[Filter]): The filter to apply to the chunks to return.

        Returns:
            List[Search]: A list of Search objects containing the retrieved chunks.
        """
        collections = self.get_collections(collection_ids=collection_ids, user=user)
        if len(set(collection.model for collection in collections)) > 1:
            raise DifferentCollectionsModelsException()

        model = collections[0].model
        response = self.models[model].embeddings.create(input=[prompt], model=model)
        vector = response.data[0].embedding

        chunks = []
        for collection in collections:
            results = self.qdrant.search(
                collection_name=collection.id, query_vector=vector, limit=k, score_threshold=score_threshold, with_payload=True, query_filter=filter
            )
            for result in results:
                result.payload["metadata"]["collection"] = collection.id
            chunks.extend(results)

        # sort by similarity score and get top k
        chunks = sorted(chunks, key=lambda x: x.score, reverse=True)[:k]
        searches = [
            Search(score=chunk.score, chunk=Chunk(id=chunk.id, content=chunk.payload["content"], metadata=chunk.payload["metadata"]))
            for chunk in chunks
        ]

        return searches

    def get_collections(self, user: User, collection_ids: List[str] = [], count_documents: bool = False) -> List[Collection]:
        """
        Get metadata of collections.

        Args:
            user (User): The user retrieving the collections.
            collection_ids (List[str]): List of collection ids to retrieve metadata for. If is an empty list, all collections will be considered.
            count_documents (bool): Whether to count the documents in the collections. Special Qdrant optimization.


        Returns:
            List[Collection]: A list of Collection objects containing the metadata for the specified collections.
        """
        # if no collection ids are provided, get all collections
        must = [HasIdCondition(has_id=collection_ids)] if collection_ids else []
        should = [
            FieldCondition(key="user", match=MatchAny(any=[user.id])),
            FieldCondition(key="type", match=MatchAny(any=[PUBLIC_COLLECTION_TYPE])),
        ]
        filter = Filter(must=must, should=should)

        records = self.qdrant.scroll(collection_name=self.METADATA_COLLECTION_ID, scroll_filter=filter, limit=1000, offset=None)
        data, offset = records[0], records[1]
        while offset is not None:
            records = self.qdrant.scroll(collection_name=self.METADATA_COLLECTION_ID, scroll_filter=filter, limit=1000, offset=offset)
            data.extend(records[0])
            offset = records[1]

        # sanity check: remove collection that does not exist
        existing_collection_ids = [collection.name for collection in self.qdrant.get_collections().collections]
        data = [collection for collection in data if collection.id in existing_collection_ids]

        # check if collection ids are valid
        existing_collection_ids = [collection.id for collection in data]
        for collection_id in collection_ids:
            if collection_id not in existing_collection_ids:
                raise CollectionNotFoundException()

        collections = list()
        for collection in data:
            document_count = (
                self.qdrant.count(
                    collection_name=self.DOCUMENT_COLLECTION_ID,
                    count_filter=Filter(must=[FieldCondition(key="collection_id", match=MatchAny(any=[collection.id]))]),
                ).count
                if count_documents
                else None
            )

            collections.append(
                Collection(
                    id=collection.id,
                    name=collection.payload.get("name"),
                    type=collection.payload.get("type"),
                    model=collection.payload.get("model"),
                    user=collection.payload.get("user"),
                    description=collection.payload.get("description"),
                    created_at=collection.payload.get("created_at"),
                    documents=document_count,
                )
            )

        return collections

    def create_collection(self, collection_id: str, collection_name: str, collection_model: str, collection_type: str, user: User) -> None:
        """
        Create a collection, if collection already exists, return the collection id.

        Args:
            collection_id (str): The id of the collection to create.
            collection_name (str): The name of the collection to create.
            collection_model (str): The model of the collection to create.
            collection_type (str): The type of the collection to create.
            user (User): The user creating the collection.
        """
        if self.models[collection_model].type != EMBEDDINGS_MODEL_TYPE:
            raise WrongModelTypeException()

        if user.role != ROLE_LEVEL_2 and collection_type == PUBLIC_COLLECTION_TYPE:
            raise WrongCollectionTypeException()

        # create metadata
        metadata = {
            "name": collection_name,
            "type": collection_type,
            "model": collection_model,
            "user": user.id,
            "description": None,
            "created_at": round(time.time()),
        }
        self.qdrant.upsert(collection_name=self.METADATA_COLLECTION_ID, points=[PointStruct(id=collection_id, payload=dict(metadata), vector={})])

        # create collection
        self.qdrant.create_collection(
            collection_name=collection_id, vectors_config=VectorParams(size=self.models[collection_model].vector_size, distance=Distance.COSINE)
        )

    def delete_collection(self, collection_id: str, user: User) -> None:
        """
        Delete a collection and all its associated data.

        Args:
            collection_id (str): The id of the collection to delete.
            user (User): The user deleting the collection.
        """
        collection = self.get_collections(collection_ids=[collection_id], user=user)[0]

        if user.role != ROLE_LEVEL_2 and collection.type == PUBLIC_COLLECTION_TYPE:
            raise WrongCollectionTypeException()

        self.qdrant.delete_collection(collection_name=collection.id)
        self.qdrant.delete(collection_name=self.METADATA_COLLECTION_ID, points_selector=PointIdsList(points=[collection.id]))

    def get_chunks(self, collection_id: str, document_id: str, user: User, limit: Optional[int] = 10, offset: Optional[int] = None) -> List[Chunk]:
        """
        Get chunks from a collection and a document.

        Args:
            collection_id (str): The id of the collection to get chunks from.
            document_id (str): The id of the document to get chunks from.
            user (User): The user retrieving the chunks.
            limit (Optional[int]): The number of chunks to return.
            offset (Optional[int]): The offset of the chunks to return.

        Returns:
            List[Chunk]: A list of Chunk objects containing the retrieved chunks.
        """
        collection = self.get_collections(collection_ids=[collection_id], user=user)[0]

        filter = Filter(must=[FieldCondition(key="metadata.document_id", match=MatchAny(any=[document_id]))])
        data = self.qdrant.scroll(collection_name=collection.id, scroll_filter=filter, limit=limit, offset=offset)[0]
        chunks = [Chunk(id=chunk.id, content=chunk.payload["content"], metadata=ChunkMetadata(**chunk.payload["metadata"])) for chunk in data]

        return chunks

    def get_documents(self, collection_id: str, user: User, limit: Optional[int] = 10, offset: Optional[int] = None) -> List[Document]:
        """
        Get documents from a collection.

        Args:
            collection_id (str): The id of the collection to get documents from.
            user (User): The user retrieving the documents.
            limit (Optional[int]): The number of documents to return.
            offset (Optional[int]): The offset of the documents to return.

        Returns:
            List[Document]: A list of Document objects containing the retrieved documents.
        """
        collection = self.get_collections(collection_ids=[collection_id], user=user)[0]

        filter = Filter(must=[FieldCondition(key="collection_id", match=MatchAny(any=[collection_id]))])
        data = self.qdrant.scroll(collection_name=self.DOCUMENT_COLLECTION_ID, scroll_filter=filter, limit=limit, offset=offset)[0]
        documents = list()
        for document in data:
            chunks_count = self.qdrant.count(
                collection_name=collection.id,
                count_filter=Filter(must=[FieldCondition(key="metadata.document_id", match=MatchAny(any=[document.id]))]),
            ).count
            documents.append(Document(id=document.id, name=document.payload["name"], created_at=document.payload["created_at"], chunks=chunks_count))

        return documents

    def delete_document(self, collection_id: str, document_id: str, user: User):
        """
        Delete a document from a collection.

        Args:
            collection_id (str): The id of the collection to delete the document from.
            document_id (str): The id of the document to delete.
            user (User): The user deleting the document.
        """
        collection = self.get_collections(collection_ids=[collection_id], user=user)[0]

        if user.role != ROLE_LEVEL_2 and collection.type == PUBLIC_COLLECTION_TYPE:
            raise WrongCollectionTypeException()

        # delete chunks
        filter = Filter(must=[FieldCondition(key="metadata.document_id", match=MatchAny(any=[document_id]))])
        self.qdrant.delete(collection_name=collection.id, points_selector=FilterSelector(filter=filter))

        # delete document
        self.qdrant.delete(collection_name=self.DOCUMENT_COLLECTION_ID, points_selector=PointIdsList(points=[document_id]))
