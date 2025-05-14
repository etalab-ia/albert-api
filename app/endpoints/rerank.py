from fastapi import APIRouter, Request, Security

from app.helpers import AccessController
from app.schemas.rerank import RerankRequest, Reranks
from app.utils.lifespan import context
from app.utils.variables import ENDPOINT__RERANK

router = APIRouter()


@router.post(path=ENDPOINT__RERANK, dependencies=[Security(dependency=AccessController())], status_code=200)
async def rerank(request: Request, body: RerankRequest) -> Reranks:
    """
    Creates an ordered array with each text assigned a relevance score, based on the query.
    """

    model = context.models(model=body.model)
    client = model.get_client(endpoint=ENDPOINT__RERANK)
    response = await client.forward_request(method="POST", json=body.model_dump())

    return Reranks(**response.json())
