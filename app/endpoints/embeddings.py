from fastapi import APIRouter, Request, Security
import httpx

from app.schemas.embeddings import Embeddings, EmbeddingsRequest
from app.schemas.security import User
from app.utils.config import settings
from app.utils.exceptions import ContextLengthExceededException, WrongModelTypeException
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit
from app.utils.variables import EMBEDDINGS_MODEL_TYPE

router = APIRouter()


@router.post("/embeddings")
@limiter.limit(settings.default_rate_limit, key_func=lambda request: check_rate_limit(request=request))
async def embeddings(request: Request, body: EmbeddingsRequest, user: User = Security(check_api_key)) -> Embeddings:
    """
    Embedding API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/embeddings/create for the API specification.
    """

    client = clients.models[body.model]
    if client.type != EMBEDDINGS_MODEL_TYPE:
        raise WrongModelTypeException()

    url = f"{client.base_url}embeddings"
    headers = {"Authorization": f"Bearer {client.api_key}"}

    async with httpx.AsyncClient(timeout=20) as async_client:
        response = await async_client.request(method="POST", url=url, headers=headers, json=body.model_dump())
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if "`inputs` must have less than" in e.response.text:
                raise ContextLengthExceededException()
            raise e

        data = response.json()

        return Embeddings(**data)
