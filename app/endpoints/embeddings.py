from fastapi import APIRouter, Request, Security

from app.helpers import RateLimit
from app.schemas.embeddings import Embeddings, EmbeddingsRequest
from app.schemas.users import AuthenticatedUser
from app.utils.lifespan import context
from app.utils.variables import ENDPOINT__EMBEDDINGS

router = APIRouter()


@router.post(path=ENDPOINT__EMBEDDINGS)
async def embeddings(request: Request, body: EmbeddingsRequest, user: AuthenticatedUser = Security(dependency=RateLimit())) -> Embeddings:
    """
    Creates an embedding vector representing the input text.
    """

    model = context.models.get(model=body.model, user=user)
    client = model.get_client(endpoint=ENDPOINT__EMBEDDINGS)
    response = await client.forward_request(method="POST", json=body.model_dump())

    return Embeddings(**response.json())
