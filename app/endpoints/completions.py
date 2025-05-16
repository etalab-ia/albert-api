from fastapi import APIRouter, Request, Security
from fastapi.responses import JSONResponse
from app.helpers import AccessController
from app.schemas.completions import CompletionRequest, Completions
from app.utils.lifespan import context
from app.utils.variables import ENDPOINT__COMPLETIONS
from app.utils.usage_decorator import log_usage

router = APIRouter()


@router.post(path=ENDPOINT__COMPLETIONS, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Completions)
@log_usage
async def completions(request: Request, body: CompletionRequest) -> JSONResponse:
    """
    Completion API similar to OpenAI's API.
    """

    model = context.models(model=body.model)
    client = model.get_client(endpoint=ENDPOINT__COMPLETIONS)
    response = await client.forward_request(request=request, method="POST", json=body.model_dump())

    return JSONResponse(content=Completions(**response.json()).model_dump(), status_code=response.status_code)
