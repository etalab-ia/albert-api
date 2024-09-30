from typing import Optional, Union
import uuid

from fastapi import APIRouter, Response, Security, HTTPException
from fastapi.responses import JSONResponse
from app.helpers import VectorStore
from app.schemas.collections import Collection, Collections, CollectionRequest
from app.utils.lifespan import clients
from app.utils.security import check_api_key

router = APIRouter()


@router.get("/collections/{collection}")
@router.get("/collections")
async def get_collections(collection: Optional[str] = None, user: str = Security(check_api_key)) -> Union[Collection, Collections]:
    """
    Get list of collections.

    Args:
        collection (str): ID of the collection.
    """

    vectorstore = VectorStore(clients=clients, user=user)
    try:
        collection_ids = [collection] if collection else []
        data = vectorstore.get_collection_metadata(collection_ids=collection_ids)
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if collection:
        return data[0]

    return Collections(data=data)


@router.post("/collections")
async def create_collection(request: CollectionRequest, user: str = Security(check_api_key)) -> Response:
    """
    Create a new private collection.

    Args:
        request (CreateCollectionRequest): Request body.
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


@router.delete("/collections/{collection}")
async def delete_collections(collection: Optional[str] = None, user: str = Security(check_api_key)) -> Response:
    """
    Delete private collections.

    Args:
        collection (str, optional): ID of the collection. If not provided, all collections for the user are deleted.
    """
    vectorstore = VectorStore(clients=clients, user=user)
    try:
        vectorstore.delete_collection(collection_id=collection)
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Response(status_code=204)
