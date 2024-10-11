from typing import List

from fastapi import APIRouter, Security

from app.helpers import SearchOnInternet
from app.schemas.search import Search, Searches, SearchRequest
from app.schemas.security import User
from app.utils.lifespan import clients
from app.utils.security import check_api_key
from app.utils.variables import INTERNET_COLLECTION_ID, HYBRID_SEARCH_TYPE, LEXICAL_SEARCH_TYPE, SEMANTIC_SEARCH_TYPE

router = APIRouter()


@router.post("/search")
async def search(request: SearchRequest, user: User = Security(check_api_key)) -> Searches:
    """
    Endpoint to search on the internet or in the vector store or using keywords.
    """

    data = []
    if INTERNET_COLLECTION_ID in request.collections:
        data.extend(_get_internet_search_result(request, user))

    if len(request.collections) > 0:
        if request.method in [SEMANTIC_SEARCH_TYPE, HYBRID_SEARCH_TYPE]:
            data.extend(_get_semantic_search_result(request, user))
        if request.method in [LEXICAL_SEARCH_TYPE, HYBRID_SEARCH_TYPE]:
            data.extend(_get_lexical_search_result(request, user))

    data = sorted(data, key=lambda x: x.score, reverse=False)[: request.k]

    return Searches(data=data)


def _get_internet_search_result(request: SearchRequest, user: User) -> List[Search]:
    request.collections.remove(INTERNET_COLLECTION_ID)
    internet = SearchOnInternet(models=clients.models)
    if len(request.collections) > 0:
        collection_model = clients.vectors.get_collections(collection_ids=request.collections, user=user)[0].model
    else:
        collection_model = None
    return internet.search(prompt=request.prompt, n=4, model_id=collection_model, score_threshold=request.score_threshold)


def _get_semantic_search_result(request: SearchRequest, user: User) -> List[Search]:
    return clients.vectors.search(
        prompt=request.prompt, collection_ids=request.collections, k=request.k, score_threshold=request.score_threshold, user=user
    )


def _get_lexical_search_result(request: SearchRequest, user: User) -> List[Search]:
    # TODO: Implement keywords search
    return []
