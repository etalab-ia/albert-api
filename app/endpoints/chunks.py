from fastapi import APIRouter, Security
from qdrant_client.http.models import Filter, HasIdCondition

from app.schemas.chunks import Chunks, Chunk, ChunkRequest
from app.utils.security import check_api_key
from app.utils.lifespan import clients
from app.helpers._vectorstore import VectorStore

router = APIRouter()


@router.get("/chunks/{collection}/{chunk}")
async def get_chunk(
    collection: str,
    chunk: str,
    user: str = Security(check_api_key),
) -> Chunk:
    """
    Get a single chunk.
    """
    vectorstore = VectorStore(clients=clients, user=user)
    ids = [chunk]
    filter = Filter(must=[HasIdCondition(has_id=ids)])
    chunks = vectorstore.get_chunks(collection_name=collection, filter=filter)
    return chunks[0]


@router.post("/chunks/{collection}")
async def get_chunks(
    collection: str,
    request: ChunkRequest,
    user: str = Security(check_api_key),
) -> Chunks:
    """
    Get multiple chunks.
    """
    vectorstore = VectorStore(clients=clients, user=user)
    ids = request.chunks
    filter = Filter(must=[HasIdCondition(has_id=ids)])
    chunks = vectorstore.get_chunks(collection_name=collection, filter=filter)
    return Chunks(data=chunks)
