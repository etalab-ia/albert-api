from fastapi import APIRouter, Request, Security

from app.helpers import RateLimit
from app.schemas.rerank import RerankRequest, Reranks
from app.schemas.users import AuthenticatedUser
from app.utils.lifespan import context
from app.utils.variables import ENDPOINT__RERANK

router = APIRouter()


@router.post(path=ENDPOINT__RERANK)
async def rerank(request: Request, body: RerankRequest, user: AuthenticatedUser = Security(RateLimit())) -> Reranks:
    """
    Creates an ordered array with each text assigned a relevance score, based on the query.
    """
    model = context.models(model=body.model, user=user)
    client = model.get_client(endpoint=ENDPOINT__RERANK)
    response = await client.forward_request(method="POST", json=body.model_dump())

    return Reranks(**response.json())
