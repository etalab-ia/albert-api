from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response, Security

from app.schemas.documents import Documents
from app.schemas.security import User
from app.utils.config import DEFAULT_RATE_LIMIT
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit

router = APIRouter()


@router.get("/documents/{collection}")
@limiter.limit(DEFAULT_RATE_LIMIT, key_func=lambda request: check_rate_limit(request=request))
async def get_documents(
    request: Request,
    collection: UUID,
    limit: Optional[int] = Query(default=10, ge=1, le=100),
    offset: Optional[UUID] = None,
    user: User = Security(check_api_key),
) -> Documents:
    """
    Get all documents ID from a collection.
    """
    collection = str(collection)
    offset = str(offset) if offset else None
    data = clients.search.get_documents(collection_id=collection, limit=limit, offset=offset, user=user)

    return Documents(data=data)


@router.delete("/documents/{collection}/{document}")
@limiter.limit(DEFAULT_RATE_LIMIT, key_func=lambda request: check_rate_limit(request=request))
async def delete_document(request: Request, collection: UUID, document: UUID, user: User = Security(check_api_key)) -> Response:
    """
    Delete a document and relative collections.
    """
    collection, document = str(collection), str(document)
    clients.search.delete_document(collection_id=collection, document_id=document, user=user)

    return Response(status_code=204)
