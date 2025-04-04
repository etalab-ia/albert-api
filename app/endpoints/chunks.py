from typing import Union
from uuid import UUID

from fastapi import APIRouter, Path, Query, Request, Security

from app.helpers import Authorization
from app.schemas.chunks import Chunk, Chunks
from app.utils.exceptions import ChunkNotFoundException
from app.utils.lifespan import context
from app.utils.variables import ENDPOINT__CHUNKS

router = APIRouter()


@router.get(path=ENDPOINT__CHUNKS + "/{document:path}/{chunk:path}", dependencies=[Security(dependency=Authorization())])
async def get_chunk(request: Request, document: int = Path(description="The document ID"), chunk: int = Path(description="The chunk ID")) -> Chunk:
    """
    Get a chunk of a document.
    """
    if not context.documents:  # no vector store available
        raise ChunkNotFoundException()

    chunks = await context.documents.get_chunks(document_id=document, chunk_id=chunk, user_id=request.app.state.user.id)

    return chunks[0]


@router.get(path=ENDPOINT__CHUNKS + "/{document}", dependencies=[Security(dependency=Authorization())])
async def get_chunks(
    request: Request,
    document: int = Path(description="The document ID"),
    limit: int = Query(default=10, ge=1, le=100, description="The number of documents to return"),
    offset: Union[int, UUID] = Query(default=0, description="The offset of the first document to return"),
) -> Chunks:
    """
    Get chunks of a document.
    """
    if not context.documents:  # no vector store available
        data = []
    else:
        data = await context.documents.get_chunks(document_id=document, limit=limit, offset=offset, user_id=request.app.state.user.id)

    return Chunks(data=data)
