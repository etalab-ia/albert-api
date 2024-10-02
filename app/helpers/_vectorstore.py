import time
from typing import List, Optional

from langchain.docstore.document import Document as LangchainDocument
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

from app.schemas.chunks import Chunk
from app.schemas.collections import Collection
from app.schemas.search import Search
from app.utils.variables import (
    EMBEDDINGS_MODEL_TYPE,
    INTERNET_COLLECTION_ID,
    METADATA_COLLECTION_ID,
    PRIVATE_COLLECTION_TYPE,
    PUBLIC_COLLECTION_TYPE,
    USER_ROLE,
)


class VectorStore:
    BATCH_SIZE = 48
    FORBIDDEN_COLLECTION_NAMES = [INTERNET_COLLECTION_ID, METADATA_COLLECTION_ID]

    def __init__(self, clients: dict, user: str):
        self.vectors = clients.vectors
        self.models = clients.models
        self.user = user

    def from_documents(self, documents: List[LangchainDocument], collection_id: str) -> None:
        """
        Add documents to a collection.

        Args:
            documents (List[Document]): A list of Langchain Document objects to add to the collection.
            model (str): The model to use for embeddings.
            collection_id (str): The id of the collection to add the documents to.
        """
        collection = self.get_collection_metadata(collection_ids=[collection_id])[0]

        if self.user.role == USER_ROLE:
            assert collection.type == PRIVATE_COLLECTION_TYPE, "Wrong collection type."

        for i in range(0, len(documents), self.BATCH_SIZE):
            batch = documents[i : i + self.BATCH_SIZE]

            texts = [document.page_content for document in batch]
            response = self.models[collection.model].embeddings.create(input=texts, model=collection.model)
            vectors = [vector.embedding for vector in response.data]

            # insert vectors
            self.vectors.upsert(
                collection_name=collection_id,
                points=[
                    PointStruct(id=document.id, vector=vector, payload={"page_content": document.page_content, "metadata": document.metadata})
                    for document, vector in zip(batch, vectors)
                ],
            )

    def search(
        self,
        prompt: str,
        collection_ids: List[str] = [],
        k: Optional[int] = 4,
        score_threshold: Optional[float] = None,
        filter: Optional[Filter] = None,
    ) -> List[Search]:
        collections = self.get_collection_metadata(collection_ids=collection_ids)
        assert len(set(collection.model for collection in collections)) == 1, "Different collections models."

        model = collections[0].model
        response = self.models[model].embeddings.create(input=[prompt], model=model)
        vector = response.data[0].embedding

        chunks = []
        for collection in collections:
            results = self.vectors.search(
                collection_name=collection.id, query_vector=vector, limit=k, score_threshold=score_threshold, with_payload=True, query_filter=filter
            )
            for result in results:
                result.payload["metadata"]["collection"] = collection.id
            chunks.extend(results)

        # sort by similarity score and get top k
        chunks = sorted(chunks, key=lambda x: x.score, reverse=True)[:k]
        searches = [
            Search(score=chunk.score, chunk=Chunk(id=chunk.id, content=chunk.payload["page_content"], metadata=chunk.payload["metadata"]))
            for chunk in chunks
        ]

        return searches

    def get_collection_metadata(self, collection_ids: List[str] = [], errors: str = "raise") -> List[Collection]:
        """
        Get metadata of collections.

        Args:
            collection_ids (List[str]): List of collection ids to retrieve metadata for. If is an empty list, all collections will be considered.
            errors (str): How to handle errors. "raise" (default) will raise an AssertionException if a collection is not found. "ignore" will skip collections that are not found.

        Returns:
            List[Collection]: A list of Collection objects containing the metadata for the specified collections.
        """
        assert errors in ["raise", "ignore"], "Errors argument must be 'raise' or 'ignore'"

        # if no collection ids are provided, get all collections
        must = [HasIdCondition(has_id=collection_ids)] if collection_ids else []
        should = [
            FieldCondition(key="user", match=MatchAny(any=[self.user.id])),
            FieldCondition(key="type", match=MatchAny(any=[PUBLIC_COLLECTION_TYPE])),
        ]
        filter = Filter(must=must, should=should)

        records = self.vectors.scroll(collection_name=METADATA_COLLECTION_ID, scroll_filter=filter, limit=1000, offset=None)
        data, offset = records[0], records[1]
        while offset is not None:
            records = self.vectors.scroll(collection_name=METADATA_COLLECTION_ID, scroll_filter=filter, limit=1000, offset=offset)
            data.extend(records[0])
            offset = records[1]

        # sanity check: remove collection that does not exist
        existing_collection_ids = [collection.name for collection in self.vectors.get_collections().collections]
        data = [collection for collection in data if collection.id in existing_collection_ids]
        existing_collection_ids = [collection.id for collection in data]

        for collection_id in collection_ids:
            if collection_id not in existing_collection_ids:
                assert errors == "ignore", "Collection not found"

        for i in range(len(data)):
            data[i] = Collection(
                id=data[i].id,
                name=data[i].payload.get("name"),
                type=data[i].payload.get("type"),
                model=data[i].payload.get("model"),
                user=data[i].payload.get("user"),
                description=data[i].payload.get("description"),
                created_at=data[i].payload.get("created_at"),
            )

        return data

    def create_collection(self, collection_id: str, collection_name: str, collection_model: str, collection_type: str) -> str:
        """
        Create a collection, if collection already exists, return the collection id.

        Args:
            collection_id (str): The id of the collection to create.
            collection_name (str): The name of the collection to create.
            collection_model (str): The model of the collection to create.
            collection_type (str): The type of the collection to create.

        Returns:
            str: The collection id.
        """
        assert collection_name not in self.FORBIDDEN_COLLECTION_NAMES, "Forbidden collection name."
        assert self.models[collection_model].type == EMBEDDINGS_MODEL_TYPE, "Wrong model type."

        if self.user.role == USER_ROLE:
            assert collection_type == PRIVATE_COLLECTION_TYPE, "Wrong collection type."

        collections = self.get_collection_metadata(collection_ids=[collection_id], errors="ignore")
        assert not collections, "Collection already exists."

        # create metadata
        metadata = {
            "name": collection_name,
            "type": collection_type,
            "model": collection_model,
            "user": self.user.id,
            "description": None,
            "created_at": round(time.time()),
        }
        self.vectors.upsert(collection_name=METADATA_COLLECTION_ID, points=[PointStruct(id=collection_id, payload=dict(metadata), vector={})])

        # create collection
        self.vectors.create_collection(
            collection_name=collection_id, vectors_config=VectorParams(size=self.models[collection_model].vector_size, distance=Distance.COSINE)
        )

    def delete_collection(self, collection_id: str):
        collection = self.get_collection_metadata(collection_ids=[collection_id])[0]

        if self.user.role == USER_ROLE:
            assert collection.type == PRIVATE_COLLECTION_TYPE, "Wrong collection type."

        self.vectors.delete_collection(collection_name=collection.id)
        self.vectors.delete(collection_name=METADATA_COLLECTION_ID, points_selector=PointIdsList(points=[collection.id]))

    def delete_chunks(self, collection_id: str, filter: Optional[Filter] = None):
        """
        Delete chunks from a collection.

        Args:
            collection_id (str): The id of the collection to delete chunks from.
            filter (Optional[Filter]): Optional filter to apply when deleting chunks. If no filter is provided, all chunks will be deleted.
        """
        collection = self.get_collection_metadata(collection_ids=[collection_id])[0]
        if self.user.role == USER_ROLE:
            assert collection.type == PRIVATE_COLLECTION_TYPE, "Wrong collection type."

        self.vectors.delete(collection_name=collection.id, points_selector=FilterSelector(filter=filter))

    def get_chunks(self, collection_id: str, filter: Optional[Filter] = None) -> List[Chunk]:
        """
        Get chunks from a collection.

        Args:
            collection_id (str): The id of the collection to get chunks from.
            filter (Optional[Filter]): Optional filter to apply when retrieving chunks.

        Returns:
            List[Chunk]: A list of Chunk objects containing the retrieved chunks.
        """
        collection = self.get_collection_metadata(collection_ids=[collection_id])[0]

        # @TODO: add pagination of avoid memory error
        records = self.vectors.scroll(collection_name=collection.id, scroll_filter=filter, limit=1000, offset=None)
        data, offset = records[0], records[1]
        while offset is not None:
            records = self.vectors.scroll(collection_name=collection.id, scroll_filter=filter, limit=1000, offset=offset)
            data.extend(records[0])
            offset = records[1]

        chunks = [
            Chunk(id=chunk.id, metadata=chunk.payload["metadata"] | {"collection": collection.id}, content=chunk.payload["page_content"])
            for chunk in data
        ]

        return chunks
