from typing import List

from fastapi import APIRouter, Request, Security

from app.helpers import InternetSearch
from app.schemas.search import Search, Searches, SearchRequest
from app.schemas.security import User
from app.utils.config import DEFAULT_RATE_LIMIT
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit
from app.utils.variables import INTERNET_COLLECTION_ID


router = APIRouter()


@router.post("/search")
@limiter.limit(DEFAULT_RATE_LIMIT, key_func=lambda request: check_rate_limit(request=request))
async def search(request: Request, body: SearchRequest, user: User = Security(check_api_key)) -> Searches:
    """
    Endpoint to search on the internet or with our engine client
    """
    searches = []
    if INTERNET_COLLECTION_ID in body.collections:
        body.collections.remove(INTERNET_COLLECTION_ID)
        searches.extend(_get_internet_searches(body, user))
        
    if len(body.collections) > 0:
        searches.extend(_get_engine_searches(body, user))

    searches = sorted(searches, key=lambda x: x.score, reverse=False)[: body.k]

    return Searches(data=searches)


def _get_internet_searches(body: SearchRequest, user: User) -> List[Search]:
    internet_search = InternetSearch(models=clients.models)
    if len(body.collections) > 0:
        collection_model = clients.search.get_collections(collection_ids=body.collections, user=user)[0].model
    else:
        collection_model = None
    return internet_search.query(prompt=body.prompt, n=4, model_id=collection_model, score_threshold=body.score_threshold)


def _get_engine_searches(body: SearchRequest, user: User) -> List[Search]:
    return clients.search.query(
        prompt=body.prompt, collection_ids=body.collections, k=body.k, score_threshold=body.score_threshold, user=user
    )
