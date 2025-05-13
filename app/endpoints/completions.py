from fastapi import APIRouter, Request, Security

from app.helpers import Authorization
from app.schemas.completions import CompletionRequest, Completions
from app.utils.lifespan import context
from app.utils.variables import ENDPOINT__COMPLETIONS

router = APIRouter()


@router.post(path=ENDPOINT__COMPLETIONS, dependencies=[Security(dependency=Authorization())], status_code=200)
async def completions(request: Request, body: CompletionRequest) -> Completions:
    """
    Completion API similar to OpenAI's API.
    """

    model = context.models(model=body.model)
    client = model.get_client(endpoint=ENDPOINT__COMPLETIONS)
    response = await client.forward_request(method="POST", json=body.model_dump())

    return Completions(**response.json())
