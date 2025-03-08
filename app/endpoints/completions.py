from fastapi import APIRouter, Request, Security

from app.helpers import RateLimit
from app.schemas.completions import CompletionRequest, Completions
from app.schemas.users import AuthenticatedUser
from app.utils.lifespan import models
from app.utils.variables import ENDPOINT__COMPLETIONS

router = APIRouter()


@router.post(path=ENDPOINT__COMPLETIONS)
async def completions(request: Request, body: CompletionRequest, user: AuthenticatedUser = Security(dependency=RateLimit())) -> Completions:
    """
    Completion API similar to OpenAI's API.
    """

    model = models.registry[body.model]
    client = model.get_client(endpoint=ENDPOINT__COMPLETIONS)
    response = await client.forward_request(method="POST", json=body.model_dump())

    return Completions(**response.json())
