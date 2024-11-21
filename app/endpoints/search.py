from fastapi import APIRouter, Request, Security

from app.helpers import InternetExplorer
from app.schemas.search import Searches, SearchRequest
from app.schemas.security import User
from app.utils.config import DEFAULT_RATE_LIMIT
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit
from app.utils.variables import INTERNET_COLLECTION_NAME_PASSED_AS_ID


router = APIRouter()


@router.post("/search")
@limiter.limit(DEFAULT_RATE_LIMIT, key_func=lambda request: check_rate_limit(request=request))
async def search(request: Request, body: SearchRequest, user: User = Security(check_api_key)) -> Searches:
    """
    Endpoint to search on the internet or with our engine client
    """

    # TODO: to be handled by a service top to InternetExplorer
    all_collections_with_also_a_new_internet_collection_queried = not body.collections
    need_internet_search = all_collections_with_also_a_new_internet_collection_queried or INTERNET_COLLECTION_NAME_PASSED_AS_ID in body.collections
    internet_collection = None
    if need_internet_search:
        internet_collection = InternetExplorer(model_clients=clients.models, search_client=clients.search).create_internet_collection(
            body.prompt, body.collections, user
        )
        internet_only_queried_but_no_data = len(body.collections) == 1 and not internet_collection
        if internet_only_queried_but_no_data:
            return Searches(data=[])

        if not all_collections_with_also_a_new_internet_collection_queried:
            body.collections = [collection_id for collection_id in body.collections if collection_id != INTERNET_COLLECTION_NAME_PASSED_AS_ID] + (
                [internet_collection.id] if internet_collection else []
            )

    searches = clients.search.query(
        prompt=body.prompt,
        collection_ids=body.collections,
        method=body.method,
        k=body.k,
        rff_k=body.rff_k,
        score_threshold=body.score_threshold,
        user=user,
    )

    if internet_collection:
        clients.search.delete_collection(internet_collection.id, user=user)

    return Searches(data=searches)
