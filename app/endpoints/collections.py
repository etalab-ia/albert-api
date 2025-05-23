from fastapi import APIRouter, Body, Depends, Path, Query, Request, Response, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers import AccessController
from app.schemas.collections import Collection, CollectionRequest, Collections, CollectionUpdateRequest
from app.sql.session import get_db as get_session
from app.utils.context import global_context as global_context
from app.utils.exceptions import CollectionNotFoundException
from app.utils.variables import ENDPOINT__COLLECTIONS

router = APIRouter()


@router.post(path=ENDPOINT__COLLECTIONS, dependencies=[Security(dependency=AccessController())], status_code=201)
async def create_collection(request: Request, body: CollectionRequest, session: AsyncSession = Depends(get_session)) -> JSONResponse:
    """
    Create a new collection.
    """
    if not global_context.documents:  # no vector store available
        raise CollectionNotFoundException()

    collection_id = await global_context.documents.create_collection(
        session=session,
        name=body.name,
        visibility=body.visibility,
        description=body.description,
        user_id=request.app.state.user.id,
    )

    return JSONResponse(status_code=201, content={"id": collection_id})


@router.get(
    path=ENDPOINT__COLLECTIONS + "/{collection}",
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    response_model=Collection,
)
async def get_collection(
    request: Request,
    collection: int = Path(..., description="The collection ID"),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """
    Get a collection by ID.
    """
    if not global_context.documents:  # no vector store available
        raise CollectionNotFoundException()

    collections = await global_context.documents.get_collections(
        session=session,
        collection_id=collection,
        user_id=request.app.state.user.id,
        include_public=True,
    )

    return JSONResponse(status_code=200, content=collections[0].model_dump())


@router.get(path=ENDPOINT__COLLECTIONS, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Collections)
async def get_collections(
    request: Request,
    offset: int = Query(default=0, ge=0, description="The offset of the collections to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the collections to get."),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """
    Get list of collections.
    """
    if not global_context.documents:  # no vector store available
        data = []
    else:
        data = await global_context.documents.get_collections(
            session=session,
            user_id=request.app.state.user.id,
            include_public=True,
            offset=offset,
            limit=limit,
        )

    return JSONResponse(status_code=200, content=Collections(data=data).model_dump())


@router.delete(path=ENDPOINT__COLLECTIONS + "/{collection}", dependencies=[Security(dependency=AccessController())], status_code=204)
async def delete_collections(
    request: Request,
    collection: int = Path(..., description="The collection ID"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """
    Delete a collection.
    """
    if not global_context.documents:  # no vector store available
        raise CollectionNotFoundException()

    await global_context.documents.delete_collection(
        session=session,
        user_id=request.app.state.user.id,
        collection_id=collection,
    )

    return Response(status_code=204)


@router.patch(path=ENDPOINT__COLLECTIONS + "/{collection}", dependencies=[Security(dependency=AccessController())], status_code=204)
async def update_collection(
    request: Request,
    collection: int = Path(..., description="The collection ID"),
    body: CollectionUpdateRequest = Body(..., description="The collection to update."),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """
    Update a collection.
    """
    if not global_context.documents:  # no vector store available
        raise CollectionNotFoundException()

    await global_context.documents.update_collection(
        session=session,
        user_id=request.app.state.user.id,
        collection_id=collection,
        name=body.name,
        visibility=body.visibility,
        description=body.description,
    )

    return Response(status_code=204)
