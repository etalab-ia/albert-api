from fastapi import APIRouter, Security
import httpx

from app.schemas.completions import CompletionRequest, Completions
from app.schemas.security import User
from app.utils.lifespan import clients
from app.utils.security import check_api_key

router = APIRouter()


@router.post("/completions")
async def completions(request: CompletionRequest, user: User = Security(check_api_key)) -> Completions:
    """
    Completion API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/completions/create for the API specification.
    """

    request = dict(request)
    client = clients.models[request["model"]]
    url = f"{client.base_url}completions"
    headers = {"Authorization": f"Bearer {client.api_key}"}

    async with httpx.AsyncClient(timeout=20) as async_client:
        response = await async_client.request(method="POST", url=url, headers=headers, json=request)
        response.raise_for_status()

        data = response.json()
        return Completions(**data)
