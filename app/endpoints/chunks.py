from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Security, Query

from app.helpers import VectorStore
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
    vectorstore = VectorStore(clients=clients, user=user)

    try:
        data = vectorstore.get_chunks(collection_id=collection, document_id=document, limit=limit, offset=offset)
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Chunks(data=data)
