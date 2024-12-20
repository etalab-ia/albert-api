from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response, Security

from app.schemas.documents import Documents
from app.schemas.security import User
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit
from app.utils.settings import settings

router = APIRouter()


@router.get("/documents/{collection}")
@limiter.limit(settings.rate_limit.by_key, key_func=lambda request: check_rate_limit(request=request))
async def get_documents(
    request: Request,
    collection: UUID,
    limit: Optional[int] = Query(default=10, ge=1, le=100),
    offset: Union[int, UUID] = Query(default=0),
    user: User = Security(check_api_key),
) -> Documents:
    """
    Get all documents ID from a collection.
    """
    collection = str(collection)
    data = clients.search.get_documents(collection_id=collection, limit=limit, offset=offset, user=user)

    return Documents(data=data)


@router.delete("/documents/{collection}/{document}")
@limiter.limit(settings.rate_limit.by_key, key_func=lambda request: check_rate_limit(request=request))
async def delete_document(request: Request, collection: UUID, document: UUID, user: User = Security(check_api_key)) -> Response:
    """
    Delete a document and relative collections.
    """
    collection, document = str(collection), str(document)
    clients.search.delete_document(collection_id=collection, document_id=document, user=user)

    return Response(status_code=204)
