from typing import Optional, Union

from fastapi import APIRouter, Response, Security

from app.helpers import VectorStore
from app.schemas.collections import Collection, Collections
from app.utils.config import LOGGER
from app.utils.data import delete_contents
from app.utils.lifespan import clients
from app.utils.security import check_api_key

router = APIRouter()


# @TODO: remove get one collection and a /collections/search to similarity search (remove /tools)
@router.get("/collections/{collection}")
@router.get("/collections")
async def get_collections(collection: Optional[str] = None, user: str = Security(check_api_key)) -> Union[Collection, Collections]:
    """
    Get list of collections.
    """

    vectorstore = VectorStore(clients=clients, user=user)

    collections = vectorstore.get_collection_metadata(collection_names=[collection])
    LOGGER.debug(f"collections: {collections}")
    data = []
    for row in collections:
        data.append(
            Collection(
                id=row.name,
                type=row.type,
                model=row.model,
                user=row.user,
                description=row.description,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )

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
    response = delete_contents(s3=clients["files"], vectorstore=vectorstore, collection_name=collection)

    return response
