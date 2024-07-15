import sys
import re

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

    collections = list()
    for collection in response.collections:
        if collection.name.startswith(f"{api_key}-"):
            # remove api_key prefix from collection name (see secure_data for details)
            collections.append(
                {
                    "object": "collection",
                    "name": collection.name.replace(f"{api_key}-", ""),
                    "type": "private",
                }
            )
        elif not bool(re.search("^[a-z0-9]{16}-", collection.name)):
            collections.append({"object": "collection", "name": collection.name, "type": "public"})

    response = {"object": "list", "data": collections}

    return CollectionResponse(**response)
