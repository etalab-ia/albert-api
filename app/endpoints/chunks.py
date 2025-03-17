from typing import Union
from uuid import UUID

from fastapi import APIRouter, Path, Query, Request, Security

from app.helpers import Authorization
from app.schemas.chunks import Chunks
from app.schemas.core.auth import AuthenticatedUser
from app.utils.lifespan import databases

router = APIRouter()


@router.get(path="/chunks/{collection}/{document}")
async def get_chunks(
    request: Request,
    collection: UUID = Path(description="The collection ID"),
    document: UUID = Path(description="The document ID"),
    limit: int = Query(default=10, ge=1, le=100, description="The number of documents to return"),
    offset: Union[int, UUID] = Query(default=0, description="The offset of the first document to return"),
    user: AuthenticatedUser = Security(dependency=Authorization()),
) -> Chunks:
    """
    Get chunks of a document.
    """

    collection, document = str(collection), str(document)
    data = databases.search.get_chunks(collection_id=collection, document_id=document, limit=limit, offset=offset, user=user.user)

    return Chunks(data=data)
