from fastapi import APIRouter, Request, Security

from app.helpers import Authorization
from app.schemas.rerank import RerankRequest, Reranks
from app.utils.lifespan import context
from app.utils.variables import ENDPOINT__RERANK
from app.helpers import log_usage

router = APIRouter()


@router.post(path=ENDPOINT__RERANK, dependencies=[Security(dependency=Authorization())])
@log_usage
async def rerank(request: Request, body: RerankRequest) -> Reranks:
    """
    Creates an ordered array with each text assigned a relevance score, based on the query.
    """

    model = context.models(model=body.model)
    client = model.get_client(endpoint=ENDPOINT__RERANK)
    response = await client.forward_request(method="POST", json=body.model_dump())

    return Reranks(**response.json())
