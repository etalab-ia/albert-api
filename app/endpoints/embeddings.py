from fastapi import APIRouter, Request, Security

from app.schemas.embeddings import Embeddings, EmbeddingsRequest
from app.schemas.security import User
from app.utils.lifespan import models
from app.utils.security import check_api_key
from app.utils.variables import ENDPOINT__EMBEDDINGS

router = APIRouter()


@router.post(path=ENDPOINT__EMBEDDINGS)
async def embeddings(request: Request, body: EmbeddingsRequest, user: User = Security(dependency=check_api_key)) -> Embeddings:
    """
    Creates an embedding vector representing the input text.
    """

    model = models.registry[body.model]
    client = model.get_client(endpoint=request.url.path)
    response = await client.forward_request(method="POST", json=body.model_dump())

    return Embeddings(**response.json())
