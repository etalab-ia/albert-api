from typing import Union, Optional

from fastapi import APIRouter, Security
from qdrant_client.http.models import Filter, HasIdCondition

from app.schemas.chunks import Chunks, Chunk, ChunkRequest
from app.utils.security import check_api_key
from app.utils.lifespan import clients
from app.utils.data import get_chunks, get_collection

router = APIRouter()


@router.get("/chunks/{collection}/{chunk}")
@router.post("/chunks/{collection}")
async def chunks(
    collection: str,
    chunk: Optional[str] = None,
    request: Optional[ChunkRequest] = None,
    user: str = Security(check_api_key),
) -> Union[Chunk, Chunks]:
    """
    Get a chunk.
    """

    ids = [chunk] if chunk else dict(request)["ids"]
    filter = Filter(must=[HasIdCondition(has_id=ids)])
    collection = get_collection(vectorstore=clients["vectors"], collection=collection, user=user)

    chunks = get_chunks(vectorstore=clients["vectors"], collection=collection.id, filter=filter)
    if not request:
        return chunks[0]

    return Chunks(data=chunks)
