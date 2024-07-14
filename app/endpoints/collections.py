import sys

from fastapi import APIRouter, Security

sys.path.append("..")
from schemas.collections import CollectionResponse
from utils.security import check_api_key
from utils.lifespan import clients

router = APIRouter()


@router.get("/collections")
def collections(api_key: str = Security(check_api_key)) -> CollectionResponse:
    """
    Get list of collections.
    """

    response = clients["vectors"].get_collections()
    collections = [
        # remove api_key prefix from collection name (see secure_data for details)
        collection.replace(f"{api_key}-", "")
        for collection in response.collections
        if collection.startswith(f"{api_key}-") or collection.startswith("public-")
    ]

    response = {"object": "list", "data": collections}

    return response
