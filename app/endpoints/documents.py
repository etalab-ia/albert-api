from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Path, Query, Request, Response, Security

from app.helpers import Authorization
from app.schemas.auth import PermissionType
from app.schemas.core.auth import AuthenticatedUser
from app.schemas.documents import Documents
from app.utils.lifespan import databases

router = APIRouter()


@router.get(path="/documents/{collection}")
async def get_documents(
    request: Request,
    collection: UUID = Path(description="The collection ID"),
    limit: Optional[int] = Query(default=10, ge=1, le=100, description="The number of documents to return"),
    offset: Union[int, UUID] = Query(default=0, description="The offset of the first document to return"),
    user: AuthenticatedUser = Security(dependency=Authorization(permissions=[PermissionType.READ_PRIVATE_COLLECTION])),
) -> Documents:
    """
    Get all documents ID from a collection.
    """
    collection = str(collection)
    data = databases.search.get_documents(collection_id=collection, limit=limit, offset=offset, user=user)

    return Documents(data=data)


@router.delete(path="/documents/{collection}/{document}")
async def delete_document(
    request: Request,
    collection: UUID = Path(description="The collection ID"),
    document: UUID = Path(description="The document ID"),
    user: AuthenticatedUser = Security(dependency=Authorization(permissions=[PermissionType.DELETE_PRIVATE_COLLECTION])),
) -> Response:
    """
    Delete a document and relative collections.
    """
    collection, document = str(collection), str(document)
    await databases.search.delete_document(collection_id=collection, document_id=document, user=user)

    return Response(status_code=204)
