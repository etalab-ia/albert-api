from app.helpers._vectorstore import VectorStore
from app.schemas.chunks import Chunk, ChunkRequest, Chunks
from app.utils.lifespan import clients
from app.utils.security import check_api_key
from fastapi import APIRouter, Security
from qdrant_client.http.models import Filter, HasIdCondition
from typing import Optional, Union

router = APIRouter()

# @TODO: add pagination
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

    vectorstore = VectorStore(clients=clients, user=user)
    ids = [chunk] if chunk else dict(request)["chunks"]
    filter = Filter(must=[HasIdCondition(has_id=ids)])
    chunks = vectorstore.get_chunks(collection_name=collection, filter=filter)
    if not request:
        return chunks[0]

    return Chunks(data=chunks)
