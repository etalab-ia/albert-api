from fastapi import APIRouter, Request, Security

from app.schemas.rerank import RerankRequest, Reranks
from app.schemas.security import User
from app.utils.lifespan import models
from app.utils.security import check_api_key
from app.utils.variables import ENDPOINT__RERANK

router = APIRouter()


@router.post(path=ENDPOINT__RERANK)
async def rerank(request: Request, body: RerankRequest, user: User = Security(check_api_key)) -> Reranks:
    """
    Creates an ordered array with each text assigned a relevance score, based on the query.
    """
    model = models.registry[body.model]
    client = model.get_client(endpoint=ENDPOINT__RERANK)
    response = await client.forward_request(method="POST", json=body.model_dump())

    return Reranks(data=response.json())
