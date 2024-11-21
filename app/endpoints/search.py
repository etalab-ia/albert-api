from fastapi import APIRouter, Request, Security

from app.helpers import InternetExplorer
from app.schemas.search import Searches, SearchRequest
from app.schemas.security import User
from app.utils.config import settings
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit
from app.utils.variables import INTERNET_COLLECTION_DISPLAY_ID


router = APIRouter()


@router.post("/search")
@limiter.limit(settings.default_rate_limit, key_func=lambda request: check_rate_limit(request=request))
async def search(request: Request, body: SearchRequest, user: User = Security(check_api_key)) -> Searches:
    """
    Endpoint to search on the internet or with our engine client
    """

    # TODO: to be handled by a service top to InternetExplorer
    need_internet_search = not body.collections or INTERNET_COLLECTION_DISPLAY_ID in body.collections
    internet_chunks = []
    if need_internet_search:
        internet_explorer = InternetExplorer(
            model_clients=clients.models,
            search_client=clients.search,
            method=settings.internet.type,
            api_key=settings.internet.args.get("api_key"),
        )
        internet_chunks = internet_explorer.get_chunks(prompt=body.prompt)

        if internet_chunks:
            internet_collection = internet_explorer.create_temporary_internet_collection(internet_chunks, body.collections, user)

        if INTERNET_COLLECTION_DISPLAY_ID in body.collections:
            body.collections.remove(INTERNET_COLLECTION_DISPLAY_ID)
            if not body.collections and not internet_chunks:
                return Searches(data=[])
            if internet_chunks:
                body.collections.append(internet_collection.id)

    searches = clients.search.query(
        prompt=body.prompt,
        collection_ids=body.collections,
        method=body.method,
        k=body.k,
        rff_k=body.rff_k,
        score_threshold=body.score_threshold,
        user=user,
    )

    if internet_chunks:
        clients.search.delete_collection(internet_collection.id, user=user)

    return Searches(data=searches)
