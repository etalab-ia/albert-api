from typing import Union, Optional

from fastapi import APIRouter, Security, HTTPException, Response
from botocore.exceptions import ClientError

from app.schemas.collections import CollectionResponse, Collection
from app.utils.security import check_api_key, secure_data
from app.utils.lifespan import clients
from app.utils.data import get_all_collections

router = APIRouter()


@router.get("/collections/{collection}")
@router.get("/collections")
@secure_data
async def get_collections(
    collection: Optional[str] = None, api_key: str = Security(check_api_key)
) -> Union[Collection, CollectionResponse]:
    """
    Get list of collections.
    """
    collections = get_all_collections(vectorstore=clients["vectors"], api_key=api_key)

    if collection is not None:
        if collection not in collections:
            raise HTTPException(status_code=404, detail="Collection not found.")

        type = "public" if collection.startswith("public-") else "private"
        collection = collection.replace(f"{api_key}-", "")

        return Collection(id=collection, type=type)

    data = list()
    for collection in collections:
        if collection.startswith(f"{api_key}-"):
            data.append(Collection(id=collection.replace(f"{api_key}-", ""), type="private"))
        else:
            data.append(Collection(id=collection, type="public"))

    return CollectionResponse(data=data)


@router.delete("/collections/{collection}")
@router.delete("/collections")
@secure_data
async def delete_collections(
    collection: Optional[str] = None, api_key: str = Security(check_api_key)
) -> Union[Collection, CollectionResponse]:
    """
    Get private collections and relative files.
    """

    collections = get_all_collections(vectorstore=clients["vectors"], api_key=api_key)
    collections = [collection for collection in collections if not collection.startswith("public-")]

    if collection is not None:
        if collection not in collections:
            raise HTTPException(status_code=404, detail="Collection not found.")
        collections = [collection]

    for collection in collections:
        try:
            clients["files"].head_bucket(Bucket=collection)
        except ClientError:
            raise HTTPException(status_code=404, detail="Files not found")

        objects = clients["files"].list_objects_v2(Bucket=collection)
        if "Contents" in objects:
            objects = [{"Key": obj["Key"]} for obj in objects["Contents"]]
            clients["files"].delete_objects(Bucket=collection, Delete={"Objects": objects})

        clients["files"].delete_bucket(Bucket=collection)
        clients["vectors"].delete_collection(collection)

    return Response(status_code=204)
