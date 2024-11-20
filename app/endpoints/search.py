from fastapi import APIRouter, Request, Security

from app.helpers import InternetSearch
from app.schemas.search import Searches, SearchRequest
from app.schemas.security import User
from app.utils.config import DEFAULT_RATE_LIMIT
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit
from app.utils.variables import INTERNET_COLLECTION_ID, HYBRID_SEARCH_TYPE, LEXICAL_SEARCH_TYPE, SEMANTIC_SEARCH_TYPE


router = APIRouter()


@router.post("/search")
@limiter.limit(DEFAULT_RATE_LIMIT, key_func=lambda request: check_rate_limit(request=request))
async def search(request: Request, body: SearchRequest, user: User = Security(check_api_key)) -> Searches:
    """
    Endpoint to search on the internet or with our engine client
    """

    searches_count = 0
    if INTERNET_COLLECTION_ID in body.collections:
        searches_count += 1
    searches_count += 2 if body.method == HYBRID_SEARCH_TYPE else 1
    limit_per_query = body.k // searches_count

    searches_list = []

    if INTERNET_COLLECTION_ID in body.collections:
        body.collections.remove(INTERNET_COLLECTION_ID)
        searches_list.append(
            InternetSearch(models=clients.models).query(
                prompt=body.prompt,
                n=limit_per_query,
                model_id=clients.search.get_collections(collection_ids=body.collections, user=user)[0].model if len(body.collections) > 0 else None,
                score_threshold=body.score_threshold,
            )
        )

    if len(body.collections) > 0:
        if body.method in [HYBRID_SEARCH_TYPE, SEMANTIC_SEARCH_TYPE]:
            searches_list.append(
                clients.search.query(
                    prompt=body.prompt,
                    collection_ids=body.collections,
                    method=SEMANTIC_SEARCH_TYPE,
                    k=limit_per_query,
                    score_threshold=body.score_threshold,
                    user=user,
                )
            )
        if body.method in [HYBRID_SEARCH_TYPE, LEXICAL_SEARCH_TYPE]:
            searches_list.append(
                clients.search.query(
                    prompt=body.prompt,
                    collection_ids=body.collections,
                    method=LEXICAL_SEARCH_TYPE,
                    k=limit_per_query,
                    score_threshold=body.score_threshold,
                    user=user,
                )
            )

    searches = clients.search.build_ranked_searches(searches_list=searches_list, limit=body.k)

    return Searches(data=searches)
