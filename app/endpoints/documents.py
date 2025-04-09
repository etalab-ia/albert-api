from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, Response, Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers import Authorization
from app.schemas.documents import Document, Documents
from app.sql.session import get_db as get_session
from app.utils.exceptions import CollectionNotFoundException, DocumentNotFoundException
from app.utils.lifespan import context
from app.utils.variables import ENDPOINT__DOCUMENTS

router = APIRouter()


@router.get(path=ENDPOINT__DOCUMENTS + "/{document:path}", dependencies=[Security(dependency=Authorization())])
async def get_document(
    request: Request,
    document: int = Path(description="The document ID"),
    session: AsyncSession = Depends(get_session),
) -> Document:
    """
    Get a document by ID.
    """
    if not context.documents:  # no vector store available
        raise DocumentNotFoundException()

    documents = await context.documents.get_documents(session=session, document_id=document, user_id=request.app.state.user.id)

    return documents[0]


@router.get(path=ENDPOINT__DOCUMENTS, dependencies=[Security(dependency=Authorization())])
async def get_documents(
    request: Request,
    collection: Optional[int] = Query(default=None, description="Filter documents by collection ID"),
    limit: Optional[int] = Query(default=10, ge=1, le=100, description="The number of documents to return"),
    offset: Union[int, UUID] = Query(default=0, description="The offset of the first document to return"),
    session: AsyncSession = Depends(get_session),
) -> Documents:
    """
    Get all documents ID from a collection.
    """

    if not context.documents:  # no vector store available
        if collection:
            raise CollectionNotFoundException()
        data = []
    else:
        data = await context.documents.get_documents(
            session=session,
            collection_id=collection,
            limit=limit,
            offset=offset,
            user_id=request.app.state.user.id,
        )

    return Documents(data=data)


@router.delete(path=ENDPOINT__DOCUMENTS + "/{document:path}", dependencies=[Security(dependency=Authorization())])
async def delete_document(
    request: Request,
    document: int = Path(description="The document ID"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """
    Delete a document and relative collections.
    """
    if not context.documents:  # no vector store available
        raise DocumentNotFoundException()

    await context.documents.delete_document(session=session, document_id=document, user_id=request.app.state.user.id)

    return Response(status_code=204)
