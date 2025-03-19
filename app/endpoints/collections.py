from typing import Union

from fastapi import APIRouter, Path, Query, Request, Response, Security
from fastapi.responses import JSONResponse

from app.helpers import Authorization
from app.schemas.auth import PermissionType
from app.schemas.collections import Collection, CollectionRequest, Collections, CollectionVisibility
from app.utils.lifespan import context
from app.utils.variables import COLLECTION_DISPLAY_ID__INTERNET
from app.schemas.core.auth import UserInfo
from app.utils.exceptions import CollectionNotFoundException

router = APIRouter()


@router.post(path="/collections")
async def create_collection(
    request: Request,
    body: CollectionRequest,
    user: int = Security(dependency=Authorization(permissions=[PermissionType.CREATE_PRIVATE_COLLECTION])),
) -> JSONResponse:
    """
    Create a new collection.
    """

    collection_id = context.iam.create_collection(user_id=user, type=body.type, description=body.description)

    return JSONResponse(status_code=201, content={"id": collection_id})


@router.get(path="/collections")
async def get_collections(
    request: Request,
    offset: int = Query(default=0, ge=0, description="The offset of the collections to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the collections to get."),
    user: int = Security(dependency=Authorization()),
) -> Union[Collection, Collections]:
    """
    Get list of collections.
    """
    internet_collection = Collection(
        id=COLLECTION_DISPLAY_ID__INTERNET,
        name=COLLECTION_DISPLAY_ID__INTERNET,
        type=CollectionVisibility.PUBLIC,
        description="Use this collection to search on the internet.",
    )

    data = await context.iam.get_collections(user_id=user, include_public=True, offset=offset, limit=limit)
    data.append(internet_collection)

    return Collections(data=data)


@router.delete(path="/collections/{collection}")  # fmt: off
async def delete_collections(
    request: Request,
    collection: int = Path(..., description="The collection ID"),
    user: UserInfo = Security(dependency=Authorization(permissions=[PermissionType.DELETE_PRIVATE_COLLECTION])),
) -> Response:
    """
    Delete a collection.
    """
    if collection not in user.private_collections:
        raise CollectionNotFoundException()

    await context.iam.delete_collection(collection_id=collection)

    return Response(status_code=204)
