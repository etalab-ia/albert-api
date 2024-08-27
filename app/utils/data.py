from typing import List, Optional

from fastapi import HTTPException, Response
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchAny, PointIdsList, FilterSelector
from boto3 import client as Boto3Client
from botocore.exceptions import ClientError
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.schemas.chunks import Chunk
from app.schemas.collections import Collection, Collections
from app.utils.config import LOGGER
from app.schemas.config import METADATA_COLLECTION, PUBLIC_COLLECTION_TYPE, PRIVATE_COLLECTION_TYPE


def get_chunks(
    vectorstore: QdrantClient,
    collection: str,
    filter: Optional[Filter] = None,
) -> List[Chunk]:
    try:
        chunks = vectorstore.scroll(
            collection_name=collection,
            with_payload=True,
            with_vectors=False,
            scroll_filter=filter,
            limit=100,  # @TODO: add pagination
        )[0]
    except Exception:
        raise HTTPException(status_code=404, detail="chunk not found.")

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
        collection = get_collection(vectorstore=vectorstore, user=user, collection=collection)
        lanchain_qdrant = QdrantVectorStore(
            client=vectorstore,
            embedding=embedding,
            collection_name=collection.id,
        )
        docs.extend(lanchain_qdrant.similarity_search_with_score(prompt, k=k, filter=filter))
    # sort by similarity score and get top k
    docs = sorted(docs, key=lambda x: x[1], reverse=True)[:k]
    docs = [doc[0] for doc in docs]

    return docs


def get_collections(vectorstore: QdrantClient, user: str, type: str = "all") -> Collections:
    """
    Get all collections from a vectorstore.

    Parameters:
        vectorstore (Qdrant): The vectorstore to get the collections from.
        user (str): The user to get the collections for.
        type (str): The type of collections to get. "all" (default) will get all collections. "public" will get only public collections. "private" will get only private collections.

    Returns:
        Collections: The collections metadata.
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

    return Collections(data=[Collection(**row.payload) for row in data])


def get_collection(
    vectorstore: QdrantClient, user: str, collection: str, type: str = "all", errors: str = "raise"
) -> Optional[Collection]:
    """
    Get a collection from a vectorstore.

    Parameters:
        vectorstore (Qdrant): The vectorstore to get the collection from.
        collection (str): The name of the collection to get.
        user (str): The user to get the collection for.
        type (str): The type of collection to get. "all" (default) will get all collections. "public" will get only public collections. "private" will get only private collections.
        errors (str): How to handle errors. "raise" (default) will raise an HTTPException if the collection is not found. "ignore" will return None if the collection is not found.

    Returns:
        Collection: The collection metadata. None if the collection is not found and errors is "ignore".
    """
    assert errors in ["raise", "ignore"], "errors must be 'raise' or 'ignore'"
    assert type in [
        "all",
        PUBLIC_COLLECTION_TYPE,
        PRIVATE_COLLECTION_TYPE,
    ], "type must be 'all', 'public' or 'private'"

    must = [FieldCondition(key="name", match=MatchAny(any=[collection]))]
    if type == "all":
        should = [
            FieldCondition(key="user", match=MatchAny(any=[user])),
            FieldCondition(key="type", match=MatchAny(any=[PUBLIC_COLLECTION_TYPE])),
        ]
    elif type == PUBLIC_COLLECTION_TYPE:
        must.append(FieldCondition(key="type", match=MatchAny(any=[PUBLIC_COLLECTION_TYPE])))
        should = []
    elif type == PRIVATE_COLLECTION_TYPE:
        must.append(FieldCondition(key="user", match=MatchAny(any=[user])))

    filter = Filter(must=must, should=should)
    data = vectorstore.scroll(collection_name=METADATA_COLLECTION, scroll_filter=filter)[0]
    LOGGER.debug(f"{collection} collection: {data}")

    if data:
        return Collection(**data[0].payload)
    elif errors == "raise":
        raise HTTPException(status_code=404, detail="Collection not found.")


def delete_contents(
    s3: Boto3Client,
    vectorstore: QdrantClient,
    user: str,
    collection: Optional[str] = None,
    file: Optional[str] = None,
) -> Response:
    if collection:
        collection = get_collection(vectorstore=vectorstore, user=user, collection=collection)
        if collection.type == PUBLIC_COLLECTION_TYPE:
            raise HTTPException(status_code=400, detail="A public collection can not deleted")
        collections = [collection]

    else:
        collections = get_collections(
            vectorstore=vectorstore, user=user, type=PRIVATE_COLLECTION_TYPE
        )

    for collection in collections:
        try:
            s3.head_bucket(Bucket=collection.id)
        except ClientError:
            raise HTTPException(status_code=404, detail=f"Files not found for collection {collection}")  # fmt: off

        objects = s3.list_objects_v2(Bucket=collection.id).get("Contents", [])
        objects = [{"Key": object["Key"]} for object in objects]
        LOGGER.debug(f"objects: {objects}")

        # if bucket is empty, delete it and the collection
        if not objects:
            s3.delete_bucket(Bucket=collection.id)
            vectorstore.delete_collection(collection.id)
            vectorstore.delete(collection_name=METADATA_COLLECTION, points_selector=PointIdsList(points=[collection.id]))  # fmt: off

        # delete all files
        elif file is None:
            # delete bucket, collection and metadata collection
            s3.delete_objects(Bucket=collection.id, Delete={"Objects": objects})
            s3.delete_bucket(Bucket=collection.id)
            vectorstore.delete_collection(collection.id)
            vectorstore.delete(collection_name=METADATA_COLLECTION, points_selector=PointIdsList(points=[collection.id]))  # fmt: off

        # delete a file and his chunks
        else:
            if file not in [object["Key"] for object in objects]:
                raise HTTPException(status_code=404, detail=f"File not found in the collection {collection}")  # fmt: off

            s3.delete_object(Bucket=collection.id, Key=file)
            filter = Filter(must=[FieldCondition(key="metadata.file_id", match=MatchAny(any=[file]))])  # fmt: off
            vectorstore.delete(
                collection_name=collection.id, points_selector=FilterSelector(filter=filter)
            )

            # if the deleted file is the last, delete bucket and collection
            if len(objects) == 1:
                # delete bucket, collection and metadata collection
                s3.delete_objects(Bucket=collection.id, Delete={"Objects": objects})
                s3.delete_bucket(Bucket=collection.id)
                vectorstore.delete_collection(collection.id)
                vectorstore.delete(collection_name=METADATA_COLLECTION, points_selector=PointIdsList(points=[collection.id]))  # fmt: off

    return Response(status_code=204)
