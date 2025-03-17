from typing import Union
import uuid
from uuid import UUID

from fastapi import APIRouter, Path, Request, Response, Security
from fastapi.responses import JSONResponse

from app.helpers import Authorization
from app.schemas.auth import PermissionType
from app.schemas.collections import Collection, CollectionRequest, Collections
from app.schemas.core.auth import AuthenticatedUser
from app.utils.lifespan import databases, context
from app.utils.variables import COLLECTION_DISPLAY_ID__INTERNET, COLLECTION_TYPE__PUBLIC

router = APIRouter()


@router.post(path="/collections")
async def create_collection(
    request: Request,
    body: CollectionRequest,
    user: AuthenticatedUser = Security(dependency=Authorization(permissions=[PermissionType.CREATE_PRIVATE_COLLECTION])),
) -> Response:
    """
    Create a new collection.
    """

    collection_id = str(uuid.uuid4())
    await databases.search.create_collection(
        collection_id=collection_id,
        collection_name=body.name,
        collection_model=body.model,
        collection_type=body.type,
        collection_description=body.description,
        user=user.user,
    )

    context.auth.create_collection(collection_id=collection_id, user=user.user, type=body.type)

    return JSONResponse(status_code=201, content={"id": collection_id})


@router.get(path="/collections")
async def get_collections(
    request: Request,
    user: AuthenticatedUser = Security(dependency=Authorization()),
) -> Union[Collection, Collections]:
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
    request: Request,
    collection: UUID = Path(..., description="The collection ID"),
    user: AuthenticatedUser = Security(dependency=Authorization(permissions=[PermissionType.DELETE_PRIVATE_COLLECTION])),
) -> Response:
    """
    Delete a collection.
    """

    collection = str(collection)
    await databases.search.delete_collection(collection_id=collection, user=user.user)

    return Response(status_code=204)
