from fastapi import APIRouter, Request, Security

from app.schemas.completions import CompletionRequest, Completions
from app.schemas.security import User
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit
from app.utils.settings import settings

router = APIRouter()


@router.post(path="/completions", deprecated=True)
@limiter.limit(limit_value=settings.rate_limit.by_user, key_func=lambda request: check_rate_limit(request=request))
async def completions(request: Request, body: CompletionRequest, user: User = Security(dependency=check_api_key)) -> Completions:
    """
    Completion API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/completions/create for the API specification.
    """

    model = clients.models[body.model]
    client = model.get_client(endpoint="completions")
    response = await client.forward_request(endpoint="completions", method="POST", json=body.model_dump())

    return Completions(**response.json())
