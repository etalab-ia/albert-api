from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Security, Query

from app.schemas.chunks import Chunks
from app.schemas.security import User
from app.utils.lifespan import clients
from app.utils.security import check_api_key

router = APIRouter()


@router.get("/chunks/{collection}/{document}")
async def get_chunks(
    collection: UUID,
    document: UUID,
    limit: Optional[int] = Query(default=10, ge=1, le=10),
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
