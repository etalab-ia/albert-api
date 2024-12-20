from fastapi import APIRouter, Request, Security

from app.helpers import InternetManager, SearchManager
from app.schemas.search import Searches, SearchRequest
from app.schemas.security import User
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit
from app.utils.settings import settings

router = APIRouter()


@router.post(path="/search")
@limiter.limit(limit_value=settings.rate_limit.by_key, key_func=lambda request: check_rate_limit(request=request))
async def search(request: Request, body: SearchRequest, user: User = Security(dependency=check_api_key)) -> Searches:
    """
    Endpoint to search on the internet or with our search client.
    """

    body = await request.json()
    body = SearchRequest(**body)

    search_manager = SearchManager(
        model_clients=clients.models,
        search_client=clients.search,
        internet_manager=InternetManager(
            model_clients=clients.models,
            internet_client=clients.internet,
            default_language_model_id=settings.internet.default_language_model,
            default_embeddings_model_id=settings.internet.default_embeddings_model,
        ),
    )

    data = search_manager.query(collections=body.collections, prompt=body.prompt, method=body.method, k=body.k, rff_k=body.rff_k, user=user)

    return Searches(data=data)
