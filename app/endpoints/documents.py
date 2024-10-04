from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, Security, Query

from app.helpers import VectorStore
from app.schemas.documents import Documents
from app.schemas.security import User
from app.utils.lifespan import clients
from app.utils.security import check_api_key

router = APIRouter()


@router.get("/documents/{collection}")
async def get_documents(
    collection: UUID, limit: Optional[int] = Query(default=10, ge=1, le=10), offset: Optional[UUID] = None, user: User = Security(check_api_key)
) -> Documents:
    """
    Get all documents ID from a collection.
    """
    collection = str(collection)
    offset = str(offset) if offset else None
    vectorstore = VectorStore(clients=clients, user=user)

    try:
        data = vectorstore.get_documents(collection_id=collection, limit=limit, offset=offset)
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Documents(data=data)


@router.delete("/documents/{collection}/{document}")
async def delete_document(
    collection: UUID,
    document: UUID,
    user: User = Security(check_api_key),
) -> Response:
    """
    Delete a document and relative collections.
    """
    collection, document = str(collection), str(document)
    vectorstore = VectorStore(clients=clients, user=user)

    # @TODO: raise 404 if file not found
    try:
        vectorstore.delete_document(collection_id=collection, document_id=document)
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Response(status_code=204)
