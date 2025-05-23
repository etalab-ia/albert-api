from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, Response, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers import AccessController
from app.schemas.documents import Document, Documents
from app.sql.session import get_db as get_session
from app.utils.context import global_context
from app.utils.exceptions import CollectionNotFoundException, DocumentNotFoundException
from app.utils.usage_decorator import log_usage
from app.utils.variables import ENDPOINT__DOCUMENTS

router = APIRouter()


@router.get(path=ENDPOINT__DOCUMENTS + "/{document:path}", dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Document)  # fmt: off
async def get_document(
    request: Request,
    document: int = Path(description="The document ID"),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """
    Get a document by ID.
    """
    if not global_context.documents:  # no vector store available
        raise DocumentNotFoundException()

    documents = await global_context.documents.get_documents(session=session, document_id=document, user_id=request.app.state.user.id)

    return JSONResponse(content=documents[0].model_dump(), status_code=200)


@router.get(path=ENDPOINT__DOCUMENTS, dependencies=[Security(dependency=AccessController())], status_code=200)
async def get_documents(
    request: Request,
    collection: Optional[int] = Query(default=None, description="Filter documents by collection ID"),
    limit: Optional[int] = Query(default=10, ge=1, le=100, description="The number of documents to return"),
    offset: Union[int, UUID] = Query(default=0, description="The offset of the first document to return"),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """
    Get all documents ID from a collection.
    """

    if not global_context.documents:  # no vector store available
        if collection:
            raise CollectionNotFoundException()

        return Documents(data=[])

    data = await global_context.documents.get_documents(
        session=session,
        collection_id=collection,
        limit=limit,
        offset=offset,
        user_id=request.app.state.user.id,
    )

    return JSONResponse(content=Documents(data=data).model_dump(), status_code=200)


@router.delete(path=ENDPOINT__DOCUMENTS + "/{document:path}", dependencies=[Security(dependency=AccessController())], status_code=204)
@log_usage
async def delete_document(
    request: Request,
    document: int = Path(description="The document ID"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """
    Delete a document and relative collections.
    """
    if not global_context.documents:  # no vector store available
        raise DocumentNotFoundException()

    await global_context.documents.delete_document(session=session, document_id=document, user_id=request.app.state.user.id)

    return Response(status_code=204)
