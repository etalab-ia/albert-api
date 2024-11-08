from fastapi import APIRouter, Request, Security

from app.helpers import Search
from app.schemas.search import Searches, SearchRequest
from app.schemas.security import User
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit
from app.utils.settings import settings

router = APIRouter()


@router.post(path="/search")
@limiter.limit(limit_value=settings.default_rate_limit, key_func=lambda request: check_rate_limit(request=request))
async def search(request: Request, body: SearchRequest, user: User = Security(dependency=check_api_key)) -> Searches:
    """
    Endpoint to search on the internet or with our search client.
    """
    data = Search(search_client=clients.search, internet_client=clients.internet).query(
        collections=body.collections, prompt=body.prompt, method=body.method, k=body.k, rff_k=body.rff_k, user=user
    )

    return Searches(data=data)
