from fastapi import APIRouter, Request, Security

from app.helpers import SearchManager
from app.schemas.search import Searches, SearchRequest
from app.schemas.security import User
from app.utils.lifespan import databases, models, internet
from app.utils.security import check_api_key

router = APIRouter()


@router.post(path="/search")
async def search(request: Request, body: SearchRequest, user: User = Security(dependency=check_api_key)) -> Searches:
    """
    Get relevant chunks from the collections and a query.
    """

    body = await request.json()
    body = SearchRequest(**body)

    search_manager = SearchManager(models=models.registry, search=databases.search, internet=internet.search)
    data = await search_manager.query(collections=body.collections, prompt=body.prompt, method=body.method, k=body.k, rff_k=body.rff_k, user=user)

    return Searches(data=data)
