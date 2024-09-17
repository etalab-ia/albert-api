import time
import uuid
from typing import List, Optional

from fastapi import HTTPException
from qdrant_client.http.models import Distance, FieldCondition, Filter, MatchAny, PointIdsList, PointStruct, VectorParams

from app.schemas.chunks import Chunk
from langchain.docstore.document import Document
from app.schemas.collections import CollectionMetadata
from app.schemas.config import EMBEDDINGS_MODEL_TYPE, METADATA_COLLECTION, PRIVATE_COLLECTION_TYPE, PUBLIC_COLLECTION_TYPE


class VectorStore:
    BATCH_SIZE = 32

    def __init__(self, clients: dict, user: str):
        self.vectors = clients["vectors"]
        self.models = clients["models"]
        self.user = user

    def from_documents(self, documents: List[Document], model: str, collection_name: str) -> None:
        """
        Add documents to a collection.

        Parameters:
            documents (List[Document]): A list of Langchain Document objects to add to the collection.
            model (str): The model to use for embeddings.
            collection_name (str): The name of the collection to add the documents to.
        """

        collection = self.get_collection_metadata(collection_names=[collection_name])[0]
        if collection.model != model:
            raise HTTPException(status_code=400, detail=f"Model {collection.model} does not match {model}")

        for i in range(0, len(documents), self.BATCH_SIZE):
            batch = documents[i : i + self.BATCH_SIZE]

            texts = [document.page_content for document in batch]
            response = self.models[model].embeddings.create(input=texts, model=model)
            vectors = [vector.embedding for vector in response.data]

            # insert vectors
            self.vectors.upsert(
                collection_name=collection.id,
                points=[
                    PointStruct(
                        id=document.id,
                        vector=vector,
                        payload={
                            "page_content": document.page_content,
                            "metadata": document.metadata,
                        },
                    )
                    for document, vector in zip(batch, vectors)
                ],
            )

    def search(
        self,
        prompt: str,
        model: str,
        collection_names: List[str],
        k: Optional[int] = 4,
        score_threshold: Optional[float] = None,
        filter: Optional[Filter] = None,
    ) -> List[Chunk]:
        response = self.models[model].embeddings.create(input=[prompt], model=model)
        vector = response.data[0].embedding

        chunks = []
        collections = self.get_collection_metadata(collection_names=collection_names)
        for collection in collections:
            if collection.model != model:
                raise HTTPException(status_code=400, detail=f"Model {collection.model} does not match {model}")

            results = self.vectors.search(
                collection_name=collection.id,
                query_vector=vector,
                limit=k,
                score_threshold=score_threshold,
                with_payload=True,
                query_filter=filter,
            )
            for i, result in enumerate(results):
                results[i] = result.model_dump()
                results[i]["collection"] = collection.name

            chunks.extend(results)

        # sort by similarity score and get top k
        chunks = sorted(chunks, key=lambda x: x["score"], reverse=True)[:k]
        chunks = [
            Chunk(id=chunk["id"], collection=chunk["collection"], content=chunk["payload"]["page_content"], metadata=chunk["payload"]["metadata"])
            for chunk in chunks
        ]

        return chunks

    def get_collection_metadata(self, collection_names: List[str] = [], type: str = "all", errors: str = "raise") -> List[CollectionMetadata]:
        """
        Get metadata of collections.

        Parameters:
            collection_names (List[str]): List of collection names to retrieve metadata for. If is an empty list, all collections will be considered.
            type (str): The type of collections to get. "all" (default) will get all collections. "public" will get only public collections. "private" will get only private collections.
            errors (str): How to handle errors. "raise" (default) will raise an HTTPException if a collection is not found. "ignore" will skip collections that are not found.

        Returns:
            List[CollectionMetadata]: A list of CollectionMetadata objects containing the metadata for the specified collections.
        """
        assert errors in ["raise", "ignore"], "errors must be 'raise' or 'ignore'"
        assert type in ["all", PUBLIC_COLLECTION_TYPE, PRIVATE_COLLECTION_TYPE], "type must be 'all', 'public' or 'private'"

        metadata = []
        collection_names = [collection for collection in collection_names if collection is not None]
        if not collection_names:
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
            for collection_name in collection_names:
                must = [FieldCondition(key="name", match=MatchAny(any=[collection_name]))]
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
                    raise HTTPException(status_code=404, detail=f"Collection {collection_name} not found")
                metadata.extend(data)

        # @TODO: the 2 following checks, they are still needed ?
        # remove collection that does not exist
        existing_collection_ids = [collection.name for collection in self.vectors.get_collections().collections]
        metadata = [collection for collection in metadata if collection.id in existing_collection_ids]

        # sort by updated_at and remove duplicates collections with same names (keep the latest version), concerns only public collections
        sorted_data = sorted(metadata, key=lambda x: x.payload.get("updated_at", 0), reverse=False)
        metadata = list({item.payload["name"]: item for item in sorted_data if "name" in item.payload}.values())

        for i in range(len(metadata)):
            metadata[i] = CollectionMetadata(
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

    def create_collection(self, collection_name: str, model: str) -> str:
        """
        Create a collection, if collection already exists, return the collection id.

        Parameters:
            collection (str): The name of the collection to create.
            vectorstore (Qdrant): The vectorstore to create the collection in.
            embeddings_model (str): The embeddings model to use.
            user (str): The user to create the collection for.

        Returns:
            str: The collection id.
        """
        if collection_name == "":
            raise HTTPException(status_code=400, detail="Collection name is required")

        if self.models[model].type != EMBEDDINGS_MODEL_TYPE:
            raise HTTPException(status_code=400, detail="Model type must be {EMBEDDINGS_MODEL_TYPE}")

        collections = self.get_collection_metadata(collection_names=[collection_name], type="all", errors="ignore")

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
            collection_id = str(uuid.uuid4())

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

        Parameters:
            collection_name (str): The name of the collection to get chunks from.
            filter (Optional[Filter]): Optional filter to apply when retrieving chunks.

        Returns:
            List[Chunk]: A list of Chunk objects containing the retrieved chunks.
        """
        collection = self.get_collection_metadata(collection_names=[collection_name], type="all")[0]
        chunks = self.vectors.scroll(
            collection_name=collection.id,
            with_payload=True,
            with_vectors=False,
            scroll_filter=filter,
            limit=100,  # @TODO: add pagination
        )[0]
        chunks = [
            Chunk(collection=collection_name, id=chunk.id, metadata=chunk.payload["metadata"], content=chunk.payload["page_content"])
            for chunk in chunks
        ]

        return chunks
