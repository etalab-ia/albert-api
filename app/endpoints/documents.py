from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Path, Query, Request, Response, Security

from app.helpers import RateLimit
from app.schemas.documents import Documents
from app.schemas.security import User
from app.utils.lifespan import databases

router = APIRouter()


@router.get(path="/documents/{collection}")
async def get_documents(
    request: Request,
    collection: UUID = Path(description="The collection ID"),
    limit: Optional[int] = Query(default=10, ge=1, le=100, description="The number of documents to return"),
    offset: Union[int, UUID] = Query(default=0, description="The offset of the first document to return"),
    user: User = Security(RateLimit()),
) -> Documents:
    """
    Get all documents ID from a collection.
    """
    collection = str(collection)
    data = databases.search.get_documents(collection_id=collection, limit=limit, offset=offset, user=user)

    return Documents(data=data)


@router.delete(path="/documents/{collection}/{document}")
async def delete_document(
    request: Request,
    collection: UUID = Path(description="The collection ID"),
    document: UUID = Path(description="The document ID"),
    user: User = Security(RateLimit()),
) -> Response:
    """
    Delete a document and relative collections.
    """
    collection, document = str(collection), str(document)
    await databases.search.delete_document(collection_id=collection, document_id=document, user=user)

    return Response(status_code=204)
