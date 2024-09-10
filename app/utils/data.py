from typing import List, Optional
import time
import uuid

from fastapi import HTTPException, Response
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Filter,
    FieldCondition,
    MatchAny,
    PointIdsList,
    FilterSelector,
    VectorParams,
    Distance,
    PointStruct,
)
from boto3 import client as Boto3Client
from botocore.exceptions import ClientError
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.schemas.chunks import Chunk
from app.schemas.collections import Collection, Collections
from app.utils.config import LOGGER
from app.schemas.config import (
    METADATA_COLLECTION,
    PUBLIC_COLLECTION_TYPE,
    PRIVATE_COLLECTION_TYPE,
    EMBEDDINGS_MODEL_TYPE,
)
from app.utils.lifespan import clients


def get_collection_id(
    vectorstore: QdrantClient, user: str, collection: str, type: str = "all", errors: str = "raise"
) -> Optional[str]:
    """
    Get a collection internal ID.

    Parameters:
        vectorstore (Qdrant): The vectorstore to get the collection from.
        collection (str): The name of the collection to get.
        user (str): The user to get the collection for.
        type (str): The type of collection to get. "all" (default) will get all collections. "public" will get only public collections. "private" will get only private collections.
        errors (str): How to handle errors. "raise" (default) will raise an HTTPException if the collection is not found. "ignore" will return None if the collection is not found.

    Returns:
        str: The collection id.

    """
    assert errors in ["raise", "ignore"], "errors must be 'raise' or 'ignore'"
    assert type in [
        "all",
        PUBLIC_COLLECTION_TYPE,
        PRIVATE_COLLECTION_TYPE,
    ], "type must be 'all', 'public' or 'private'"

    must = [FieldCondition(key="id", match=MatchAny(any=[collection]))]
    should = []
    if type == "all":
        should = [
            FieldCondition(key="user", match=MatchAny(any=[user])),
            FieldCondition(key="type", match=MatchAny(any=[PUBLIC_COLLECTION_TYPE])),
        ]
    elif type == PUBLIC_COLLECTION_TYPE:
        must.append(FieldCondition(key="type", match=MatchAny(any=[PUBLIC_COLLECTION_TYPE])))

    elif type == PRIVATE_COLLECTION_TYPE:
        must.append(FieldCondition(key="user", match=MatchAny(any=[user])))

    filter = Filter(must=must, should=should)
    data = vectorstore.scroll(collection_name=METADATA_COLLECTION, scroll_filter=filter)[0]
    LOGGER.debug(f"{collection} collection: {data}")

    if data:
        return data[0].id

    elif errors == "raise":
        raise HTTPException(status_code=404, detail="Collection not found.")


def get_collection_metadata(
    collection, vectorstore: QdrantClient, user: str, type: str = "all", errors: str = "raise"
) -> Collection:
    """
    Get a collection metadata.

    Parameters:
        collection (str): The name of the collection to get.
        vectorstore (Qdrant): The vectorstore to get the collection from.
        user (str): The user to get the collection for.
        type (str): The type of collection to get. "all" (default) will get all collections. "public" will get only public collections. "private" will get only private collections.
        errors (str): How to handle errors. "raise" (default) will raise an HTTPException if the collection is not found. "ignore" will return None if the collection is not found.

    Returns:
        Collection: The collection metadata.
    """
    collection_id = get_collection_id(
        vectorstore=vectorstore, user=user, collection=collection, type=type, errors=errors
    )
    metadata = vectorstore.retrieve(collection_name=METADATA_COLLECTION, ids=[collection_id])

    if metadata:
        return Collection(**metadata[0].payload)


def get_collection_ids(vectorstore: QdrantClient, user: str, type: str = "all") -> Collections:
    """
    Get ID of collections from a vectorstore.

    Parameters:
        vectorstore (Qdrant): The vectorstore to get the collections from.
        user (str): The user to get the collections for.
        type (str): The type of collections to get. "all" (default) will get all collections. "public" will get only public collections. "private" will get only private collections.

    Returns:
        list: The collections ids.
    """
    assert type in [
        "all",
        PUBLIC_COLLECTION_TYPE,
        PRIVATE_COLLECTION_TYPE,
    ], "type must be 'all', 'public' or 'private'"

    if type == "all":
        must = []
        should = [
            FieldCondition(key="user", match=MatchAny(any=[user])),
            FieldCondition(key="type", match=MatchAny(any=[PUBLIC_COLLECTION_TYPE])),
        ]
    elif type == PUBLIC_COLLECTION_TYPE:
        must = [FieldCondition(key="type", match=MatchAny(any=[PUBLIC_COLLECTION_TYPE]))]
        should = []
    elif type == PRIVATE_COLLECTION_TYPE:
        must = [FieldCondition(key="user", match=MatchAny(any=[user]))]
        should = []

    filter = Filter(must=must, should=should)
    data = vectorstore.scroll(collection_name=METADATA_COLLECTION, scroll_filter=filter)[0]
    LOGGER.debug(f"collections: {data}")

    ids = [row.id for row in data]
    return ids


def get_collections_metadata(
    vectorstore: QdrantClient, user: str, type: str = "all"
) -> Collections:
    """
    Get metadata of collections from a vectorstore.

    Parameters:
        vectorstore (Qdrant): The vectorstore to get the collections from.
        user (str): The user to get the collections for.
        type (str): The type of collections to get. "all" (default) will get all collections. "public" will get only public collections. "private" will get only private collections.

    Returns:
        list: The collections metadata.
    """
    collection_ids = get_collection_ids(vectorstore=vectorstore, user=user, type=type)
    collections = vectorstore.retrieve(collection_name=METADATA_COLLECTION, ids=collection_ids)
    data = [Collection(**collection.payload) for collection in collections]

    return Collections(data=data)


def create_collection(
    collection: str,
    vectorstore: QdrantClient,
    embeddings_model: str,
    user: str,
) -> str:
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

    collection_name = collection

    if clients["models"][embeddings_model].type != EMBEDDINGS_MODEL_TYPE:
        raise HTTPException(status_code=400, detail="Model type must be {EMBEDDINGS_MODEL_TYPE}")

    collection_id = get_collection_id(
        vectorstore=vectorstore, user=user, collection=collection, type="all", errors="ignore"
    )

    # if collection already exists
    if collection_id:
        metadata = get_collection_metadata(
            vectorstore=vectorstore, user=user, collection=collection, type="all"
        )
        if metadata.type == PUBLIC_COLLECTION_TYPE:
            raise HTTPException(status_code=400, detail="A public collection already exists with the same name")  # fmt: off
        if metadata.model != embeddings_model:
            raise HTTPException(status_code=400, detail="Collection already exists with a different model.")  # fmt: off

        # update metadata
        metadata = dict(metadata)
        metadata["updated_at"] = round(time.time())
        vectorstore.upsert(
            collection_name=METADATA_COLLECTION,
            points=[
                PointStruct(
                    id=collection_id,
                    payload=dict(metadata),
                    vector={},
                )
            ],
        )
        return collection_id

    else:
        collection_id = str(uuid.uuid4())

        # create metadata
        metadata = {
            "id": collection_name,
            "type": PRIVATE_COLLECTION_TYPE,
            "model": embeddings_model,
            "user": user,
            "description": None,
            "created_at": round(time.time()),
            "updated_at": round(time.time()),
        }
        vectorstore.upsert(
            collection_name=METADATA_COLLECTION,
            points=[
                PointStruct(
                    id=collection_id,
                    payload=dict(metadata),
                    vector={},
                )
            ],
        )
        # create collection
        vectorstore.create_collection(
            collection_name=collection_id,
            vectors_config=VectorParams(
                size=clients["models"][embeddings_model].vector_size, distance=Distance.COSINE
            ),
        )

    return collection_id


def delete_contents(
    s3: Boto3Client,
    vectorstore: QdrantClient,
    user: str,
    collection: Optional[str] = None,
    file: Optional[str] = None,
) -> Response:
    if collection:
        collection_id = get_collection_id(
            vectorstore=vectorstore, user=user, collection=collection, type=PRIVATE_COLLECTION_TYPE
        )
        collection_ids = [collection_id]
    else:
        collection_ids = get_collection_ids(
            vectorstore=vectorstore, user=user, type=PRIVATE_COLLECTION_TYPE
        )

    for collection_id in collection_ids:
        try:
            s3.head_bucket(Bucket=collection_id)
        except ClientError:
            raise HTTPException(status_code=404, detail=f"Files not found for collection {collection}")  # fmt: off

        objects = s3.list_objects_v2(Bucket=collection_id).get("Contents", [])
        objects = [{"Key": object["Key"]} for object in objects]
        LOGGER.debug(f"objects: {objects}")

        # if bucket is empty, delete it and the collection
        if not objects:
            s3.delete_bucket(Bucket=collection_id)
            vectorstore.delete_collection(collection_id)
            vectorstore.delete(collection_name=METADATA_COLLECTION, points_selector=PointIdsList(points=[collection_id]))  # fmt: off

        # delete all files
        elif file is None:
            # delete bucket, collection and metadata collection
            s3.delete_objects(Bucket=collection_id, Delete={"Objects": objects})
            s3.delete_bucket(Bucket=collection_id)
            vectorstore.delete_collection(collection_id)
            vectorstore.delete(collection_name=METADATA_COLLECTION, points_selector=PointIdsList(points=[collection_id]))  # fmt: off

        # delete a file and his chunks
        else:
            if file not in [object["Key"] for object in objects]:
                raise HTTPException(status_code=404, detail=f"File not found in the collection {collection}")  # fmt: off

            s3.delete_object(Bucket=collection_id, Key=file)
            filter = Filter(must=[FieldCondition(key="metadata.file_id", match=MatchAny(any=[file]))])  # fmt: off
            vectorstore.delete(
                collection_name=collection_id, points_selector=FilterSelector(filter=filter)
            )

            # if the deleted file is the last, delete bucket and collection
            if len(objects) == 1:
                # delete bucket, collection and metadata collection
                s3.delete_objects(Bucket=collection_id, Delete={"Objects": objects})
                s3.delete_bucket(Bucket=collection_id)
                vectorstore.delete_collection(collection_id)
                vectorstore.delete(collection_name=METADATA_COLLECTION, points_selector=PointIdsList(points=[collection_id]))  # fmt: off

    return Response(status_code=204)


def search_multiple_collections(
    vectorstore: QdrantClient,
    embedding: HuggingFaceEndpointEmbeddings,
    prompt: str,
    collections: list,
    user: str,
    k: Optional[int] = 4,
    filter: Optional[dict] = None,
):
    docs = []
    for collection in collections:
        collection_id = get_collection_id(vectorstore=vectorstore, user=user, collection=collection)
        langchain_qdrant = QdrantVectorStore(
            client=vectorstore,
            embedding=embedding,
            collection_name=collection_id,
        )
        docs.extend(langchain_qdrant.similarity_search_with_score(prompt, k=k, filter=filter))
    # sort by similarity score and get top k
    docs = sorted(docs, key=lambda x: x[1], reverse=True)[:k]
    docs = [doc[0] for doc in docs]

    return docs


def get_chunks(
    vectorstore: QdrantClient,
    collection: str,
    user: str,
    filter: Optional[Filter] = None,
) -> List[Chunk]:
    collection_id = get_collection_id(
        vectorstore=vectorstore, user=user, collection=collection, type="all"
    )
    chunks = vectorstore.scroll(
        collection_name=collection_id,
        with_payload=True,
        with_vectors=False,
        scroll_filter=filter,
        limit=100,  # @TODO: add pagination
    )[0]
    data = list()
    for chunk in chunks:
        data.append(
            Chunk(
                collection=collection,
                id=chunk.id,
                metadata=chunk.payload["metadata"],
                content=chunk.payload["page_content"],
            )
        )

    return data
