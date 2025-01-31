from fastapi import APIRouter, Request, Security

from app.schemas.embeddings import Embeddings, EmbeddingsRequest
from app.schemas.security import User
from app.utils.lifespan import clients
from app.utils.security import check_api_key

router = APIRouter()


@router.post(path="/embeddings")
async def embeddings(request: Request, body: EmbeddingsRequest, user: User = Security(dependency=check_api_key)) -> Embeddings:
    """
    Embedding API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/embeddings/create for the API specification.
    """

    model = clients.models[body.model]
    client = model.get_client(endpoint="embeddings")
    response = await client.forward_request(endpoint="embeddings", method="POST", json=body.model_dump())

    return Embeddings(**response.json())
