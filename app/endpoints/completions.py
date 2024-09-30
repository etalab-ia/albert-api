from fastapi import APIRouter, HTTPException, Security
import httpx

from app.schemas.completions import CompletionRequest, Completions
from app.utils.lifespan import clients
from app.utils.security import check_api_key
from app.utils.variables import LANGUAGE_MODEL_TYPE

router = APIRouter()


@router.post("/completions")
async def completions(request: CompletionRequest, user: str = Security(check_api_key)) -> Completions:
    """
    Completion API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/completions/create for the API specification.
    """

    request = dict(request)
    client = clients["models"][request["model"]]

    if client.type != LANGUAGE_MODEL_TYPE:
        raise HTTPException(status_code=400, detail="Model is not a language model")

    url = f"{client.base_url}completions"
    headers = {"Authorization": f"Bearer {client.api_key}"}

    async with httpx.AsyncClient(timeout=20) as async_client:
        response = await async_client.request(method="POST", url=url, headers=headers, json=request)
        response.raise_for_status()
        data = response.json()
        return Completions(**data)
