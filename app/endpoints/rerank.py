from fastapi import APIRouter, Request, Security

from app.schemas.rerank import RerankRequest, Reranks
from app.schemas.security import User
from app.utils.lifespan import clients
from app.utils.security import check_api_key

router = APIRouter()


@router.post(path="/rerank")
async def rerank(request: Request, body: RerankRequest, user: User = Security(check_api_key)) -> Reranks:
    """
    Rerank a list of inputs with a language model or reranker model.
    """
    model = clients.models[body.model]
    client = model.get_client(endpoint="rerank")
    data = await client.rerank.create(prompt=body.prompt, input=body.input, model=client.model)

    return Reranks(data=data)
