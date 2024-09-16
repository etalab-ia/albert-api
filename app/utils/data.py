from app.helpers import VectorStore
from app.schemas.config import PRIVATE_COLLECTION_TYPE
from app.utils.config import LOGGER
from boto3 import client as Boto3Client
from botocore.exceptions import ClientError
from fastapi import HTTPException, Response
from qdrant_client.http.models import FieldCondition, Filter, FilterSelector, MatchAny
from typing import Optional


def delete_contents(s3: Boto3Client, vectorstore: VectorStore, collection_name: Optional[str] = None, file: Optional[str] = None) -> Response:
    
    collections = vectorstore.get_collection_metadata(collection_names=[collection_name], type=PRIVATE_COLLECTION_TYPE)

    for collection in collections:
        try:
            s3.head_bucket(Bucket=collection.id)
        except ClientError:
            vectorstore.delete_collection(collection_name=collection_name)
            continue

        objects = s3.list_objects_v2(Bucket=collection.id).get("Contents", [])
        objects = [{"Key": object["Key"]} for object in objects]
        LOGGER.debug(f"objects: {objects}")

        # if bucket is empty, delete it and the collection
        if not objects:
            s3.delete_bucket(Bucket=collection.id)
            vectorstore.delete_collection(collection_name=collection_name)

        # delete all files
        elif file is None:
            # delete bucket and collection
            s3.delete_objects(Bucket=collection.id, Delete={"Objects": objects})
            s3.delete_bucket(Bucket=collection.id)
            vectorstore.delete_collection(collection_name=collection_name)

        # delete a file and his chunks
        else:
            if file not in [object["Key"] for object in objects]:
                raise HTTPException(status_code=404, detail=f"File not found in the collection {collection}")

            s3.delete_object(Bucket=collection.id, Key=file)
            filter = Filter(must=[FieldCondition(key="metadata.file_id", match=MatchAny(any=[file]))])
            vectorstore.vectors.delete(collection_name=collection.id, points_selector=FilterSelector(filter=filter))

            # if the deleted file is the last, delete bucket and collection
            if len(objects) == 1:
                s3.delete_objects(Bucket=collection.id, Delete={"Objects": objects})
                s3.delete_bucket(Bucket=collection.id)
                vectorstore.delete_collection(collection_name=collection_name)

    return Response(status_code=204)
