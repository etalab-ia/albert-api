from typing import Union, Optional

from fastapi import APIRouter, Security
from qdrant_client.http.models import Filter, HasIdCondition

from app.schemas.chunks import ChunkResponse, Chunk, ChunkRequest
from app.utils.security import check_api_key
from app.utils.lifespan import clients
from app.utils.data import get_chunks

router = APIRouter()


@router.get("/chunks/{collection}/{chunk}")
@router.post("/chunks/{collection}")
def chunks(
    collection: str,
    chunk: Optional[str] = None,
    request: Optional[ChunkRequest] = None,
    api_key: str = Security(check_api_key),
) -> Union[Chunk, ChunkResponse]:
    """
    Get a chunk.
    """

    ids = [chunk] if chunk else dict(request)["ids"]
    filter = Filter(must=[HasIdCondition(has_id=[ids])])
    chunks = get_chunks(vectorstore=clients["vectors"], collection=collection, filter=filter)
    if not request:
        return chunks[0]

    return ChunkResponse(data=chunks)
