from fastapi import APIRouter, Request, Security, HTTPException
import httpx
import json

from app.schemas.embeddings import Embeddings, EmbeddingsRequest
from app.schemas.security import User
from app.utils.settings import settings
from app.utils.exceptions import WrongModelTypeException
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit
from app.utils.variables import EMBEDDINGS_MODEL_TYPE, DEFAULT_TIMEOUT

router = APIRouter()


@router.post(path="/embeddings")
@limiter.limit(limit_value=settings.default_rate_limit, key_func=lambda request: check_rate_limit(request=request))
async def embeddings(request: Request, body: EmbeddingsRequest, user: User = Security(dependency=check_api_key)) -> Embeddings:
    """
    Embedding API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/embeddings/create for the API specification.
    """

    client = clients.models[body.model]
    if client.type != EMBEDDINGS_MODEL_TYPE:
        raise WrongModelTypeException()

    url = f"{client.base_url}embeddings"
    headers = {"Authorization": f"Bearer {client.api_key}"}

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as async_client:
            response = await async_client.request(method="POST", url=url, headers=headers, json=body.model_dump())
            # try:
            response.raise_for_status()
            # except httpx.HTTPStatusError as e:
            #     if "`inputs` must have less than" in e.response.text:
            #         raise ContextLengthExceededException()
            #     raise e
            data = response.json()
            return Embeddings(**data)
    except Exception as e:
        raise HTTPException(status_code=e.response.status_code, detail=json.loads(e.response.text)["message"])
