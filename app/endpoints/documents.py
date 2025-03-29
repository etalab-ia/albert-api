from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Path, Query, Request, Response, Security

from app.helpers import Authorization
from app.schemas.documents import Document, Documents
from app.utils.lifespan import context
from app.utils.variables import ENDPOINT__DOCUMENTS

router = APIRouter()


@router.get(path=ENDPOINT__DOCUMENTS + "/{document:path}")
async def get_document(request: Request, document: int = Path(description="The document ID"), user: str = Security(dependency=Authorization())) -> Document:  # fmt: off
    """
    Get a document by ID.
    """

    documents = await context.documents.get_documents(document_id=document, user_id=user.user_id)

    return documents[0]


@router.get(path=ENDPOINT__DOCUMENTS)
async def get_documents(
    request: Request,
    collection: Optional[int] = Query(default=None, description="Filter documents by collection ID"),
    limit: Optional[int] = Query(default=10, ge=1, le=100, description="The number of documents to return"),
    offset: Union[int, UUID] = Query(default=0, description="The offset of the first document to return"),
    user: str = Security(dependency=Authorization()),
) -> Documents:
    """
    Get all documents ID from a collection.
    """

    data = await context.documents.get_documents(collection_id=collection, limit=limit, offset=offset, user_id=user.user_id)

    return Documents(data=data)


@router.delete(path=ENDPOINT__DOCUMENTS + "/{document:path}")
async def delete_document(
    request: Request, document: int = Path(description="The document ID"), user: str = Security(dependency=Authorization())) -> Response:  # fmt: off
    """
    Delete a document and relative collections.
    """
    await context.documents.delete_document(document_id=document, user_id=user.user_id)

    return Response(status_code=204)
