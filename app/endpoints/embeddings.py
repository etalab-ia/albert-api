from fastapi import APIRouter, Request, Security
from fastapi.responses import JSONResponse

from app.helpers import AccessController
from app.schemas.embeddings import Embeddings, EmbeddingsRequest
from app.utils.lifespan import context
from app.utils.variables import ENDPOINT__EMBEDDINGS

router = APIRouter()


@router.post(path=ENDPOINT__EMBEDDINGS, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Embeddings)
async def embeddings(request: Request, body: EmbeddingsRequest) -> JSONResponse:
    """
    Creates an embedding vector representing the input text.
    """

    model = context.models(model=body.model)
    client = model.get_client(endpoint=ENDPOINT__EMBEDDINGS)
    response = await client.forward_request(method="POST", json=body.model_dump(), additional_data={"prompt_tokens": request.app.state.prompt_tokens})

    return JSONResponse(content=Embeddings(**response.json()).model_dump(), status_code=response.status_code)
