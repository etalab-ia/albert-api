from fastapi import APIRouter, Request, Security

from app.helpers import Authorization, SearchManager
from app.schemas.core.auth import AuthenticatedUser
from app.schemas.search import Searches, SearchRequest
from app.utils.lifespan import context, databases, internet

router = APIRouter()


@router.post(path="/search")
async def search(
    request: Request,
    body: SearchRequest,
    user: AuthenticatedUser = Security(dependency=Authorization()),
) -> Searches:
    """
    Get relevant chunks from the collections and a query.
    """
    body = await request.json()
    body = SearchRequest(**body)

    search_manager = SearchManager(models=context.models, search=databases.search, internet=internet.search)
    data = await search_manager.query(collections=body.collections, prompt=body.prompt, method=body.method, k=body.k, rff_k=body.rff_k, user=user)

    return Searches(data=data)
