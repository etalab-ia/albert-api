from typing import Union
import uuid
from uuid import UUID

from fastapi import APIRouter, Path, Request, Response, Security
from fastapi.responses import JSONResponse

from app.schemas.collections import Collection, CollectionRequest, Collections
from app.schemas.security import User
from app.utils.lifespan import databases, internet
from app.utils.security import check_api_key
from app.utils.variables import COLLECTION_DISPLAY_ID__INTERNET, COLLECTION_TYPE__PUBLIC
from app.utils.exceptions import ReservedCollectionIDException

router = APIRouter()


@router.post(path="/collections")
async def create_collection(request: Request, body: CollectionRequest, user: User = Security(check_api_key)) -> Response:
    """
    Create a new collection.
    """
    if (body.name == COLLECTION_DISPLAY_ID__INTERNET) and (not internet.search):
        raise ReservedCollectionIDException()
    collection_id = str(uuid.uuid4())
    databases.search.create_collection(
        collection_id=collection_id,
        collection_name=body.name,
        collection_model=body.model,
        collection_type=body.type,
        collection_description=body.description,
        user=user,
    )

    return JSONResponse(status_code=201, content={"id": collection_id})


@router.get(path="/collections")
async def get_collections(request: Request, user: User = Security(check_api_key)) -> Union[Collection, Collections]:
    """
    Get list of collections.
    """
    internet_collection = Collection(
        id=COLLECTION_DISPLAY_ID__INTERNET,
        name=COLLECTION_DISPLAY_ID__INTERNET,
        model=None,
        type=COLLECTION_TYPE__PUBLIC,
        description="Use this collection to search on the internet.",
    )
    data = databases.search.get_collections(user=user)
    data.append(internet_collection)

    return Collections(data=data)


@router.delete(path="/collections/{collection}")
async def delete_collections(
    request: Request, collection: UUID = Path(..., description="The collection ID"), user: User = Security(check_api_key)
) -> Response:
    """
    Delete a collection.
    """
    collection = str(collection)
    databases.search.delete_collection(collection_id=collection, user=user)

    return Response(status_code=204)
