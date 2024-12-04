from fastapi import APIRouter, Request, Security

from app.schemas.rerank import RerankRequest
from app.schemas.security import User
from app.utils.settings import settings
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit
from app.utils.variables import LANGUAGE_MODEL_TYPE, RERANK_MODEL_TYPE

router = APIRouter()


@router.post("/rerank")
@limiter.limit(settings.default_rate_limit, key_func=lambda request: check_rate_limit(request=request))
async def rerank(request: Request, body: RerankRequest, user: User = Security(check_api_key)):
    """LLM based reranker."""
    client = clients.models[body.model]
    # TODO: Add rerank model based reranker

    url = f"{client.base_url}rerank"
    headers = {"Authorization": f"Bearer {client.api_key}"}

    if client.type == LANGUAGE_MODEL_TYPE:
        rerank_type = "llm_rerank"
    elif client.type == RERANK_MODEL_TYPE:
        rerank_type = "classic_rerank"

    results = clients.rerank.get_rank(body.prompt, body.inputs, body.model, rerank_type)
    return results
