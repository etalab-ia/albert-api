from uuid import UUID

from fastapi import APIRouter, HTTPException, Security
from qdrant_client.http.models import Filter, HasIdCondition

from app.helpers import VectorStore
from app.schemas.chunks import Chunk, ChunkRequest, Chunks
from app.utils.lifespan import clients
from app.utils.security import check_api_key

router = APIRouter()


@router.get("/chunks/{collection}/{chunk}")
async def get_chunk(collection: UUID, chunk: str, user: str = Security(check_api_key)) -> Chunk:
    """
    Get a single chunk.
    """
    collection = str(collection)
    vectorstore = VectorStore(clients=clients, user=user)
    ids = [chunk]
    filter = Filter(must=[HasIdCondition(has_id=ids)])
    try:
        chunks = vectorstore.get_chunks(collection_id=collection, filter=filter)
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return chunks[0]


@router.post("/chunks/{collection}")
async def get_chunks(collection: UUID, request: ChunkRequest, user: str = Security(check_api_key)) -> Chunks:
    """
    Get multiple chunks.
    """
    collection = str(collection)
    vectorstore = VectorStore(clients=clients, user=user)
    ids = request.chunks
    filter = Filter(must=[HasIdCondition(has_id=ids)])
    try:
        chunks = vectorstore.get_chunks(collection_id=collection, filter=filter)
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Chunks(data=chunks)
