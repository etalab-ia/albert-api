import time
from typing import List, Optional

from fastapi import HTTPException
from langchain.docstore.document import Document
from qdrant_client.http.models import Distance, FieldCondition, Filter, MatchAny, PointIdsList, PointStruct, VectorParams, HasIdCondition

from app.schemas.chunks import Chunk
from app.schemas.collections import Collection
from app.schemas.config import EMBEDDINGS_MODEL_TYPE, METADATA_COLLECTION, PRIVATE_COLLECTION_TYPE, PUBLIC_COLLECTION_TYPE
from app.schemas.search import Search


class VectorStore:
    BATCH_SIZE = 32
    FORBIDDEN_COLLECTION_NAMES = ["internet", "collections"]

    def __init__(self, clients: dict, user: str):
        self.vectors = clients["vectors"]
        self.models = clients["models"]
        self.user = user

    def from_documents(self, documents: List[Document], model: str, collection_id: str) -> None:
        """
        Add documents to a collection.

        Args:
            documents (List[Document]): A list of Langchain Document objects to add to the collection.
            model (str): The model to use for embeddings.
            collection_name (str): The name of the collection to add the documents to.
        """

        collection = self.get_collection_metadata(collection_ids=[collection_id])[0]
        assert collection.model != model, "Wrong model collection"

        for i in range(0, len(documents), self.BATCH_SIZE):
            batch = documents[i : i + self.BATCH_SIZE]

            texts = [document.page_content for document in batch]
            response = self.models[model].embeddings.create(input=texts, model=model)
            vectors = [vector.embedding for vector in response.data]

            # insert vectors
            self.vectors.upsert(
                collection_name=collection.id,
                points=[
                    PointStruct(id=document.id, vector=vector, payload={"page_content": document.page_content, "metadata": document.metadata})
                    for document, vector in zip(batch, vectors)
                ],
            )

    def search(
        self,
        prompt: str,
        model: str,
        collection_ids: List[str],
        k: Optional[int] = 4,
        score_threshold: Optional[float] = None,
        filter: Optional[Filter] = None,
    ) -> List[Search]:
        response = self.models[model].embeddings.create(input=[prompt], model=model)
        vector = response.data[0].embedding

        chunks = []
        collections = self.get_collection_metadata(collection_ids=collection_ids)
        for collection in collections:
            if collection.model != model:
                raise HTTPException(status_code=400, detail="Wrong model collection")

            results = self.vectors.search(
                collection_name=collection.id, query_vector=vector, limit=k, score_threshold=score_threshold, with_payload=True, query_filter=filter
            )
            for result in results:
                result.payload["metadata"]["collection"] = collection.id
            chunks.extend(results)

        # sort by similarity score and get top k
        chunks = sorted(chunks, key=lambda x: x.score, reverse=True)[:k]
        data = [
            Search(score=chunk.score, chunk=Chunk(id=chunk.id, content=chunk.payload["page_content"], metadata=chunk.payload["metadata"]))
            for chunk in chunks
        ]

        return data

    def get_collection_metadata(self, collection_ids: List[str] = [], type: str = "all", errors: str = "raise") -> List[Collection]:
        """
        Get metadata of collections.

        Args:
            collection_names (List[str]): List of collection names to retrieve metadata for. If is an empty list, all collections will be considered.
            type (str): The type of collections to get. "all" (default) will get all collections. "public" will get only public collections. "private" will get only private collections.
            errors (str): How to handle errors. "raise" (default) will raise an HTTPException if a collection is not found. "ignore" will skip collections that are not found.

        Returns:
            List[Collection]: A list of Collection objects containing the metadata for the specified collections.
        """
        assert errors in ["raise", "ignore"], "errors must be 'raise' or 'ignore'"
        assert type in ["all", PUBLIC_COLLECTION_TYPE, PRIVATE_COLLECTION_TYPE], "type must be 'all', 'public' or 'private'"

        metadata = []
        collection_ids = [collection for collection in collection_ids if collection is not None]
        if not collection_ids:
            if type == "all":
                must = []
                should = [
                    FieldCondition(key="user", match=MatchAny(any=[self.user])),
                    FieldCondition(key="type", match=MatchAny(any=[PUBLIC_COLLECTION_TYPE])),
                ]
            elif type == PUBLIC_COLLECTION_TYPE:
                must = [FieldCondition(key="type", match=MatchAny(any=[PUBLIC_COLLECTION_TYPE]))]
                should = []
            elif type == PRIVATE_COLLECTION_TYPE:
                must = [FieldCondition(key="user", match=MatchAny(any=[self.user]))]
                should = []

            filter = Filter(must=must, should=should)
            data = self.vectors.scroll(collection_name=METADATA_COLLECTION, scroll_filter=filter)[0]
            metadata.extend(data)

        else:
            for collection_id in collection_ids:
                must = [HasIdCondition(has_id=collection_id)]
                should = []
                if type == "all":
                    should = [
                        FieldCondition(key="user", match=MatchAny(any=[self.user])),
                        FieldCondition(key="type", match=MatchAny(any=[PUBLIC_COLLECTION_TYPE])),
                    ]
                elif type == PUBLIC_COLLECTION_TYPE:
                    must.append(FieldCondition(key="type", match=MatchAny(any=[PUBLIC_COLLECTION_TYPE])))

                elif type == PRIVATE_COLLECTION_TYPE:
                    must.append(FieldCondition(key="user", match=MatchAny(any=[self.user])))

                filter = Filter(must=must, should=should)
                data = self.vectors.scroll(collection_name=METADATA_COLLECTION, scroll_filter=filter)[0]
                # LOGGER.debug(f"{collection} collection: {data}")
                if not data and errors == "raise":
                    raise HTTPException(status_code=404, detail=f"Collection {collection_id} not found")
                metadata.extend(data)

        # sanity check: remove collection that does not exist
        existing_collection_ids = [collection.name for collection in self.vectors.get_collections().collections]
        metadata = [collection for collection in metadata if collection.id in existing_collection_ids]

        for i in range(len(metadata)):
            metadata[i] = Collection(
                id=metadata[i].id,
                name=metadata[i].payload.get("name"),
                type=metadata[i].payload.get("type"),
                model=metadata[i].payload.get("model"),
                user=metadata[i].payload.get("user"),
                description=metadata[i].payload.get("description"),
                created_at=metadata[i].payload.get("created_at"),
                updated_at=metadata[i].payload.get("updated_at"),
            )

        return metadata

    def create_collection(self, collection_id: str, collection_name: str, model: str) -> str:
        """
        Create a collection, if collection already exists, return the collection id.

        Args:
            collection (str): The name of the collection to create.
            vectorstore (Qdrant): The vectorstore to create the collection in.
            embeddings_model (str): The embeddings model to use.
            user (str): The user to create the collection for.

        Returns:
            str: The collection id.
        """
        # @TODO: replace by pydantic validation (path: )
        if collection_name.strip() == "":
            raise HTTPException(status_code=400, detail="Collection name is required")

        if collection_name in self.FORBIDDEN_COLLECTION_NAMES:
            raise HTTPException(status_code=400, detail="Collection name is forbidden")

        if self.models[model].type != EMBEDDINGS_MODEL_TYPE:
            raise HTTPException(status_code=400, detail="Model type must be {EMBEDDINGS_MODEL_TYPE}")

        collections = self.get_collection_metadata(collection_ids=[collection_id], type="all", errors="ignore")

        # if collection already exists
        if collections:
            collection = collections[0]
            if collection.type == PUBLIC_COLLECTION_TYPE:
                raise HTTPException(status_code=400, detail="A public collection already exists with the same name")
            if collection.model != model:
                raise HTTPException(status_code=400, detail="A collection already exists with a different model.")

            # update metadata
            metadata = dict(collection)
            metadata["updated_at"] = round(time.time())
            collection_id = metadata.pop("id")
            self.vectors.upsert(collection_name=METADATA_COLLECTION, points=[PointStruct(id=collection_id, payload=dict(metadata), vector={})])

        else:
            # create metadata
            metadata = {
                "name": collection_name,
                "type": PRIVATE_COLLECTION_TYPE,
                "model": model,
                "user": self.user,
                "description": None,
                "created_at": round(time.time()),
                "updated_at": round(time.time()),
            }
            self.vectors.upsert(collection_name=METADATA_COLLECTION, points=[PointStruct(id=collection_id, payload=dict(metadata), vector={})])

            # create collection
            self.vectors.create_collection(
                collection_name=collection_id, vectors_config=VectorParams(size=self.models[model].vector_size, distance=Distance.COSINE)
            )

        return collection_id

    def delete_collection(self, collection_name: str):
        collection = self.get_collection_metadata(collection_names=[collection_name])[0]
        self.vectors.delete_collection(collection_name=collection.id)
        self.vectors.delete(collection_name=METADATA_COLLECTION, points_selector=PointIdsList(points=[collection.id]))

    def get_chunks(self, collection_name: str, filter: Optional[Filter] = None) -> List[Chunk]:
        """
        Get chunks from a collection.

        Args:
            collection_name (str): The name of the collection to get chunks from.
            filter (Optional[Filter]): Optional filter to apply when retrieving chunks.

        Returns:
            List[Chunk]: A list of Chunk objects containing the retrieved chunks.
        """
        collection = self.get_collection_metadata(collection_names=[collection_name], type="all")[0]
        chunks = self.vectors.scroll(collection_name=collection.id, with_payload=True, with_vectors=False, scroll_filter=filter)[0]
        for chunk in chunks:
            chunk.payload["metadata"]["collection"] = collection.name
        chunks = [Chunk(id=chunk.id, metadata=chunk.payload["metadata"], content=chunk.payload["page_content"]) for chunk in chunks]

        return chunks
