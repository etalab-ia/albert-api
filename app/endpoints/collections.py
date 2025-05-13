from typing import Union

from fastapi import APIRouter, Body, Depends, Path, Query, Request, Response, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers import Authorization
from app.schemas.collections import Collection, CollectionRequest, Collections, CollectionUpdateRequest
from app.sql.session import get_db as get_session
from app.utils.exceptions import CollectionNotFoundException
from app.utils.lifespan import context
from app.utils.variables import ENDPOINT__COLLECTIONS

router = APIRouter()


@router.post(path=ENDPOINT__COLLECTIONS, dependencies=[Security(dependency=Authorization())], status_code=201)
async def create_collection(request: Request, body: CollectionRequest, session: AsyncSession = Depends(get_session)) -> JSONResponse:
    """
    Create a new collection.
    """
    if not context.documents:  # no vector store available
        raise CollectionNotFoundException()

    collection_id = await context.documents.create_collection(
        session=session,
        name=body.name,
        visibility=body.visibility,
        description=body.description,
        user_id=request.app.state.user.id,
    )

    return JSONResponse(status_code=201, content={"id": collection_id})


@router.get(path=ENDPOINT__COLLECTIONS + "/{collection}", dependencies=[Security(dependency=Authorization())], status_code=200)
async def get_collection(
    request: Request, collection: int = Path(..., description="The collection ID"), session: AsyncSession = Depends(get_session)
) -> Collection:
    """
    Get a collection by ID.
    """
    if not context.documents:  # no vector store available
        raise CollectionNotFoundException()

    collections = await context.documents.get_collections(
        session=session,
        collection_id=collection,
        user_id=request.app.state.user.id,
        include_public=True,
    )

    return collections[0]


@router.get(path=ENDPOINT__COLLECTIONS, dependencies=[Security(dependency=Authorization())], status_code=200)
async def get_collections(
    request: Request,
    offset: int = Query(default=0, ge=0, description="The offset of the collections to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the collections to get."),
    session: AsyncSession = Depends(get_session),
) -> Union[Collection, Collections]:
    """
    Get list of collections.
    """
    if not context.documents:  # no vector store available
        data = []
    else:
        data = await context.documents.get_collections(
            session=session,
            user_id=request.app.state.user.id,
            include_public=True,
            offset=offset,
            limit=limit,
        )

    return Collections(data=data)


@router.delete(path=ENDPOINT__COLLECTIONS + "/{collection}", dependencies=[Security(dependency=Authorization())], status_code=204)
async def delete_collections(
    request: Request, collection: int = Path(..., description="The collection ID"), session: AsyncSession = Depends(get_session)
) -> Response:
    """
    Delete a collection.
    """
    if not context.documents:  # no vector store available
        raise CollectionNotFoundException()

    await context.documents.delete_collection(
        session=session,
        user_id=request.app.state.user.id,
        collection_id=collection,
    )

    return Response(status_code=204)


@router.patch(path=ENDPOINT__COLLECTIONS + "/{collection}", dependencies=[Security(dependency=Authorization())], status_code=204)
async def update_collection(
    request: Request,
    collection: int = Path(..., description="The collection ID"),
    body: CollectionUpdateRequest = Body(..., description="The collection to update."),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """
    Update a collection.
    """
    if not context.documents:  # no vector store available
        raise CollectionNotFoundException()

    await context.documents.update_collection(
        session=session,
        user_id=request.app.state.user.id,
        collection_id=collection,
        name=body.name,
        visibility=body.visibility,
        description=body.description,
    )

    return Response(status_code=204)
