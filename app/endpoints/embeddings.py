import sys

from fastapi import APIRouter, Security

sys.path.append("..")
from schemas.embeddings import EmbeddingsRequest, EmbeddingResponse
from utils.lifespan import clients
from utils.security import check_api_key


router = APIRouter()


@router.post("/embeddings")
async def embeddings(
    request: EmbeddingsRequest, api_key: str = Security(check_api_key)
) -> EmbeddingResponse:
    """
    Embedding API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/embeddings/create for the API specification.
    """

    request = dict(request)
    client = clients["openai"][request["model"]]
    response = client.embeddings.create(**request)

    return EmbeddingResponse(**response)
