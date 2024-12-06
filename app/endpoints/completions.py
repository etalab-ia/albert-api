from fastapi import APIRouter, Request, Security, HTTPException
import httpx
import json

from app.schemas.completions import CompletionRequest, Completions
from app.schemas.security import User
from app.utils.settings import settings
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit
from app.utils.variables import DEFAULT_TIMEOUT

router = APIRouter()


@router.post(path="/completions")
@limiter.limit(limit_value=settings.default_rate_limit, key_func=lambda request: check_rate_limit(request=request))
async def completions(request: Request, body: CompletionRequest, user: User = Security(dependency=check_api_key)) -> Completions:
    """
    Completion API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/completions/create for the API specification.
    """
    client = clients.models[body.model]
    url = f"{client.base_url}completions"
    headers = {"Authorization": f"Bearer {client.api_key}"}

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as async_client:
            response = await async_client.request(method="POST", url=url, headers=headers, json=body.model_dump())
            response.raise_for_status()

            data = response.json()
            return Completions(**data)

    except Exception as e:
        raise HTTPException(status_code=e.response.status_code, detail=json.loads(e.response.text)["message"])
