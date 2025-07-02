from fastapi import APIRouter, Request, Security
from fastapi.responses import JSONResponse

from app.helpers._accesscontroller import AccessController
from app.schemas.completions import CompletionRequest, Completions
from app.utils.context import global_context
from app.utils.variables import ENDPOINT__COMPLETIONS

router = APIRouter()


@router.post(path=ENDPOINT__COMPLETIONS, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Completions)
async def completions(request: Request, body: CompletionRequest) -> JSONResponse:
    """
    Completion API similar to OpenAI's API.
    """

    model = global_context.model_registry(model=body.model)
    client = model.get_client(endpoint=ENDPOINT__COMPLETIONS)
    response = await client.forward_request(method="POST", json=body.model_dump())

    return JSONResponse(content=Completions(**response.json()).model_dump(), status_code=response.status_code)
