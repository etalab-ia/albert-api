from typing import Union
import uuid
from uuid import UUID

from fastapi import APIRouter, Request, Response, Security
from fastapi.responses import JSONResponse

from app.schemas.collections import Collection, CollectionRequest, Collections
from app.schemas.security import User
from app.utils.lifespan import clients
from app.utils.security import check_api_key
from app.utils.variables import INTERNET_COLLECTION_DISPLAY_ID, PUBLIC_COLLECTION_TYPE

router = APIRouter()


@router.post("/collections")
async def create_collection(request: Request, body: CollectionRequest, user: User = Security(check_api_key)) -> Response:
    """
    Create a new collection.
    """
    collection_id = str(uuid.uuid4())
    clients.search.create_collection(
        collection_id=collection_id,
        collection_name=body.name,
        collection_model=body.model,
        collection_type=body.type,
        collection_description=body.description,
        user=user,
    )

    return JSONResponse(status_code=201, content={"id": collection_id})


@router.get("/collections")
async def get_collections(request: Request, user: User = Security(check_api_key)) -> Union[Collection, Collections]:
    """
    Get list of collections.
    """
    internet_collection = Collection(
        id=INTERNET_COLLECTION_DISPLAY_ID,
        name=INTERNET_COLLECTION_DISPLAY_ID,
        model=None,
        type=PUBLIC_COLLECTION_TYPE,
        description="Use this collection to search on the internet.",
    )
    data = clients.search.get_collections(user=user)
    data.append(internet_collection)

    return Collections(data=data)


@router.delete("/collections/{collection}")
async def delete_collections(request: Request, collection: UUID, user: User = Security(check_api_key)) -> Response:
    """
    Delete a collection.
    """
    collection = str(collection)
    clients.search.delete_collection(collection_id=collection, user=user)

    return Response(status_code=204)
