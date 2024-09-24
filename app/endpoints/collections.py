from typing import Optional, Union


from fastapi import APIRouter, Response, Security, HTTPException

from app.helpers import VectorStore
from app.schemas.collections import Collection, Collections, CreateCollectionRequest
from app.utils.data import delete_contents
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

    data = vectorstore.get_collection_metadata(collection_names=[collection])
    if collection:
        return data[0]

    return Collections(data=data)


@router.delete("/collections/{collection}")
@router.delete("/collections")
async def delete_collections(collection: Optional[str] = None, user: str = Security(check_api_key)) -> Response:
    """
    Get private collections and relative files.
    """

    vectorstore = VectorStore(clients=clients, user=user)
    try:
        delete_contents(s3=clients["files"], vectorstore=vectorstore, collection_name=collection)
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Response(status_code=204)


@router.post("/collections")
async def create_collection(request: CreateCollectionRequest, user: str = Security(check_api_key)) -> Response:
    vectorstore = VectorStore(clients=clients, user=user)
    collection_id = vectorstore.create_collection(name=request.name, model=request.model)

    return Response(status_code=201)
