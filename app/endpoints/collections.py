from typing import Union

from fastapi import APIRouter, Path, Query, Request, Response, Security
from fastapi.responses import JSONResponse

from app.helpers import Authorization
from app.schemas.collections import Collection, CollectionRequest, Collections
<<<<<<< HEAD
from app.schemas.security import User
from app.utils.lifespan import databases
from app.utils.security import check_api_key
from app.utils.variables import COLLECTION_DISPLAY_ID__INTERNET, COLLECTION_TYPE__PUBLIC
from app.utils.exceptions import NoVectorStoreAvailableException
=======
from app.schemas.core.auth import UserInfo
from app.utils.exceptions import CollectionNotFoundException
from app.utils.lifespan import context
from app.utils.settings import settings
from app.utils.variables import ENDPOINT__COLLECTIONS, ENDPOINT__EMBEDDINGS
>>>>>>> e317108 (feat: refacto auth)

router = APIRouter()


@router.post(path=ENDPOINT__COLLECTIONS)
async def create_collection(request: Request, body: CollectionRequest, user: UserInfo = Security(dependency=Authorization())) -> JSONResponse:
    """
    Create a new collection.
    """
    if not context.documents:  # no vector store available
        raise CollectionNotFoundException()

    model = context.models(model=settings.general.documents_model)
    client = model.get_client(endpoint=ENDPOINT__EMBEDDINGS)
    vector_size = client.vector_size
    collection_id = await context.documents.create_collection(
        name=body.name,
        vector_size=vector_size,
        visibility=body.visibility,
        description=body.description,
        user_id=user.user_id,
    )

    return JSONResponse(status_code=201, content={"id": collection_id})


@router.get(path=ENDPOINT__COLLECTIONS)
async def get_collections(
    request: Request,
    offset: int = Query(default=0, ge=0, description="The offset of the collections to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the collections to get."),
    user: UserInfo = Security(dependency=Authorization()),
) -> Union[Collection, Collections]:
    """
    Get list of collections.
    """

    if not context.documents:  # no vector store available
        data = []
    else:
        data = await context.documents.get_collections(user_id=user.user_id, include_public=True, offset=offset, limit=limit)

    return Collections(data=data)


@router.delete(path=ENDPOINT__COLLECTIONS + "/{collection}")
async def delete_collections(
    request: Request, collection: int = Path(..., description="The collection ID"), user: UserInfo = Security(dependency=Authorization())
) -> Response:
    """
    Delete a collection.
    """
    if not context.documents:  # no vector store available
        raise CollectionNotFoundException()

    await context.documents.delete_collection(user_id=user.user_id, collection_id=collection)

    return Response(status_code=204)
