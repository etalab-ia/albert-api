from typing import Union, Optional

from fastapi import APIRouter, Security, Response

from app.schemas.collections import Collections, Collection
from app.utils.security import check_api_key
from app.utils.lifespan import clients
from app.utils.data import (
    get_collections as _get_collections,
    get_collection as _get_collection,
    delete_contents,
)
from app.utils.config import LOGGER

router = APIRouter()


@router.get("/collections/{collection}")
@router.get("/collections")
async def get_collections(
    collection: Optional[str] = None, user: str = Security(check_api_key)
) -> Union[Collection, Collections]:
    """
    Get list of collections.
    """
    if collection is None:
        collections = _get_collections(vectorstore=clients["vectors"], user=user)
        LOGGER.debug(f"collections: {collections}")
        return collections
    else:
        collection = _get_collection(
            vectorstore=clients["vectors"], user=user, collection=collection
        )
        LOGGER.debug(f"collection: {collection}")
        return collection


@router.delete("/collections/{collection}")
@router.delete("/collections")
async def delete_collections(
    collection: Optional[str] = None, user: str = Security(check_api_key)
) -> Response:
    """
    Get private collections and relative files.
    """
    response = delete_contents(
        s3=clients["files"],
        vectorstore=clients["vectors"],
        user=user,
        collection=collection,
    )
    return response
