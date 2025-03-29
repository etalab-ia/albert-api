from fastapi import APIRouter, Request, Security

from app.helpers import Authorization
from app.schemas.search import Searches, SearchRequest
from app.utils.lifespan import context
from app.utils.settings import settings
from app.utils.variables import ENDPOINT__SEARCH, ENDPOINT__EMBEDDINGS

router = APIRouter()


@router.post(path=ENDPOINT__SEARCH)
async def search(request: Request, body: SearchRequest, user: str = Security(dependency=Authorization())) -> Searches:
    """
    Get relevant chunks from the collections and a query.
    """
    model = context.models(model=settings.general.documents_model)
    client = model.get_client(endpoint=ENDPOINT__EMBEDDINGS)

    data = await context.documents.search(
        model_client=client,
        collection_ids=body.collections,
        prompt=body.prompt,
        method=body.method,
        k=body.k,
        rff_k=body.rff_k,
        user_id=user.user_id,
        web_search=body.web_search,
    )

    return Searches(data=data)
