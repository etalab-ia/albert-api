from fastapi import APIRouter, Request, Security

from app.helpers import Authorization
from app.schemas.embeddings import Embeddings, EmbeddingsRequest
from app.utils.lifespan import context
from app.utils.variables import ENDPOINT__EMBEDDINGS

router = APIRouter()


@router.post(path=ENDPOINT__EMBEDDINGS, dependencies=[Security(dependency=Authorization())])
async def embeddings(request: Request, body: EmbeddingsRequest) -> Embeddings:
    """
    Creates an embedding vector representing the input text.
    """

    model = context.models(model=body.model)
    client = model.get_client(endpoint=ENDPOINT__EMBEDDINGS)
    response = await client.forward_request(method="POST", json=body.model_dump())

    return Embeddings(**response.json())
