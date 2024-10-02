from typing import Literal, Optional, Union
import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, Security
from fastapi.responses import JSONResponse

from app.helpers import VectorStore
from app.schemas.collections import Collection, CollectionRequest, Collections
from app.schemas.security import User
from app.utils.lifespan import clients
from app.utils.security import check_api_key
from app.utils.variables import PUBLIC_COLLECTION_TYPE, INTERNET_COLLECTION_ID

router = APIRouter()


@router.post("/collections")
async def create_collection(request: CollectionRequest, user: User = Security(check_api_key)) -> Response:
    """
    Create a new collection.
    """
    vectorstore = VectorStore(clients=clients, user=user)
    collection_id = str(uuid.uuid4())
    try:
        vectorstore.create_collection(
            collection_id=collection_id, collection_name=request.name, collection_model=request.model, collection_type=request.type
        )
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return JSONResponse(status_code=201, content={"id": collection_id})


@router.get("/collections/{collection}")
@router.get("/collections")
async def get_collections(
    collection: Optional[Union[UUID, Literal["internet"]]] = None, user: User = Security(check_api_key)
) -> Union[Collection, Collections]:
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
    if collection == "internet":
        return internet_collection

    collection_ids = [str(collection)] if collection else []
    vectorstore = VectorStore(clients=clients, user=user)
    try:
        data = vectorstore.get_collection_metadata(collection_ids=collection_ids)
    except AssertionError as e:
        # TODO: return a 404 error if collection not found
        raise HTTPException(status_code=400, detail=str(e))

    if collection:
        return data[0]

    data.append(internet_collection)
    return Collections(data=data)


@router.delete("/collections/{collection}")
async def delete_collections(collection: UUID, user: User = Security(check_api_key)) -> Response:
    """
    Delete a collection.
    """
    collection = str(collection)
    vectorstore = VectorStore(clients=clients, user=user)
    try:
        vectorstore.delete_collection(collection_id=collection)
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Response(status_code=204)
