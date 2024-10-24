from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Request, Security, Query

from app.schemas.chunks import Chunks
from app.schemas.security import User
from app.utils.lifespan import clients
from app.utils.security import check_api_key, check_rate_limit
from app.utils.config import DEFAULT_RATE_LIMIT
from app.utils.lifespan import limiter

router = APIRouter()


@router.get("/chunks/{collection}/{document}")
@limiter.limit(DEFAULT_RATE_LIMIT, key_func=lambda request: check_rate_limit(request=request))
async def get_chunks(
    request: Request,
    collection: UUID,
    document: UUID,
    limit: Optional[int] = Query(default=10, ge=1, le=100),
    offset: Optional[UUID] = None,
    user: User = Security(check_api_key),
) -> Chunks:
    """
    Get a single chunk.
    """
    collection, document = str(collection), str(document)
    offset = str(offset) if offset else None
    data = clients.vectors.get_chunks(collection_id=collection, document_id=document, limit=limit, offset=offset, user=user)

    return Chunks(data=data)
