from fastapi import APIRouter, Request, Security

from app.helpers import Authorization
from app.schemas.search import Searches, SearchRequest
from app.utils.lifespan import context

router = APIRouter()


@router.post(path="/search")
async def search(
    request: Request,
    body: SearchRequest,
    user: str = Security(dependency=Authorization()),
) -> Searches:
    """
    Get relevant chunks from the collections and a query.
    """
    body = await request.json()
    body = SearchRequest(**body)

    data = await context.documents.search(
        collection_ids=body.collections, prompt=body.prompt, method=body.method, k=body.k, rff_k=body.rff_k, user_id=user.id
    )

    return Searches(data=data)
