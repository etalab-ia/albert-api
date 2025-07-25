from fastapi import APIRouter, Request, Security
from fastapi.responses import JSONResponse

from app.helpers._accesscontroller import AccessController
from app.schemas.embeddings import Embeddings, EmbeddingsRequest
from app.utils.context import global_context
from app.utils.variables import ENDPOINT__EMBEDDINGS

router = APIRouter()


@router.post(path=ENDPOINT__EMBEDDINGS, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Embeddings)
async def embeddings(request: Request, body: EmbeddingsRequest) -> JSONResponse:
    """
    Creates an embedding vector representing the input text.
    """

    async def handler(client):
        response = await client.forward_request(method="POST", json=body.model_dump())
        return JSONResponse(content=Embeddings(**response.json()).model_dump(), status_code=response.status_code)

    return await global_context.model_registry.execute_request(
        router_id=body.model,
        endpoint=ENDPOINT__EMBEDDINGS,
        handler=handler
    )
