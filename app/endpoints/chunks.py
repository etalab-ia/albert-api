from typing import Union
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._accesscontroller import AccessController
from app.schemas.chunks import Chunk, Chunks
from app.utils.depends import get_db_session
from app.utils.context import global_context, request_context
from app.utils.exceptions import ChunkNotFoundException
from app.utils.variables import ENDPOINT__CHUNKS

router = APIRouter()


@router.get(path=ENDPOINT__CHUNKS + "/{document:path}/{chunk:path}", dependencies=[Security(dependency=AccessController())], status_code=200)
async def get_chunk(
    request: Request,
    document: int = Path(description="The document ID"),
    chunk: int = Path(description="The chunk ID"),
    session: AsyncSession = Depends(get_db_session),
) -> Chunk:
    """
    Get a chunk of a document.
    """
    if not global_context.documents:  # no vector store available
        raise ChunkNotFoundException()

    chunks = await global_context.documents.get_chunks(session=session, document_id=document, chunk_id=chunk, user_id=request_context.get().user_id)

    return chunks[0]


@router.get(path=ENDPOINT__CHUNKS + "/{document}", dependencies=[Security(dependency=AccessController())], status_code=200)
async def get_chunks(
    request: Request,
    document: int = Path(description="The document ID"),
    limit: int = Query(default=10, ge=1, le=100, description="The number of documents to return"),
    offset: Union[int, UUID] = Query(default=0, description="The offset of the first document to return"),
    session: AsyncSession = Depends(get_db_session),
) -> Chunks:
    """
    Get chunks of a document.
    """
    if not global_context.documents:  # no vector store available
        data = []
    else:
        data = await global_context.documents.get_chunks(
            session=session,
            document_id=document,
            limit=limit,
            offset=offset,
            user_id=request_context.get().user_id,
        )

    return Chunks(data=data)
