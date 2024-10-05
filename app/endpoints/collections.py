from typing import Union
import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, Security
from fastapi.responses import JSONResponse


from app.schemas.collections import Collection, CollectionRequest, Collections
from app.schemas.security import User
from app.utils.lifespan import clients
from app.utils.security import check_api_key
from app.utils.variables import INTERNET_COLLECTION_ID, PUBLIC_COLLECTION_TYPE

router = APIRouter()


@router.post("/collections")
async def create_collection(request: CollectionRequest, user: User = Security(check_api_key)) -> Response:
    """
    Create a new collection.
    """
    collection_id = str(uuid.uuid4())
    try:
        clients.vectorstore.create_collection(
            collection_id=collection_id, collection_name=request.name, collection_model=request.model, collection_type=request.type, user=user
        )
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return JSONResponse(status_code=201, content={"id": collection_id})


@router.get("/collections")
async def get_collections(user: User = Security(check_api_key)) -> Union[Collection, Collections]:
    """
    Get list of collections.
    """
    internet_collection = Collection(
        id=INTERNET_COLLECTION_ID,
        name=INTERNET_COLLECTION_ID,
        model=None,
        type=PUBLIC_COLLECTION_TYPE,
        description="Use this collection to search on the internet.",
    )
    try:
        data = clients.vectorstore.get_collections(user=user)
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    data.append(internet_collection)

    return Collections(data=data)


@router.delete("/collections/{collection}")
async def delete_collections(collection: UUID, user: User = Security(check_api_key)) -> Response:
    """
    Delete a collection.
    """
    collection = str(collection)
    try:
        clients.vectorstore.delete_collection(collection_id=collection, user=user)
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Response(status_code=204)
