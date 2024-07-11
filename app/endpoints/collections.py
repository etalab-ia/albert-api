import sys

from fastapi import APIRouter, Security

sys.path.append("..")
from utils.schemas import CollectionResponse
from utils.security import check_api_key
from utils.lifespan import clients

router = APIRouter()


@router.get("/collections")
def collections(api_key: str = Security(check_api_key)) -> CollectionResponse:
    """
    Get list of collections.
    """

    response = clients["vectors"].get_collections()
    response = {"object": "list", "data": collections}

    return response
