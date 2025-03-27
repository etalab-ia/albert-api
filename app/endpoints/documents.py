from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Path, Query, Request, Response, Security

from app.helpers import Authorization
from app.schemas.documents import Documents
from app.utils.lifespan import context

router = APIRouter()


@router.get(path="/documents/{collection}")
async def get_documents(
    request: Request,
    collection: int = Path(description="The collection ID"),
    limit: Optional[int] = Query(default=10, ge=1, le=100, description="The number of documents to return"),
    offset: Union[int, UUID] = Query(default=0, description="The offset of the first document to return"),
    user: str = Security(dependency=Authorization()),
) -> Documents:
    """
    Get all documents ID from a collection.
    """

    data = await context.documents.get_documents(collection_id=collection, limit=limit, offset=offset, user_id=user.user_id)

    return Documents(data=data)


@router.delete(path="/documents/{collection}/{document}")
async def delete_document(
    request: Request,
    collection: int = Path(description="The collection ID"),
    document: int = Path(description="The document ID"),
    user: str = Security(dependency=Authorization()),
) -> Response:
    """
    Delete a document and relative collections.
    """
    await context.documents.delete_document(document_id=document, user_id=user.user_id)

    return Response(status_code=204)
