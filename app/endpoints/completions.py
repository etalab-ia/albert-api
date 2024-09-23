from fastapi import APIRouter, Security

from app.schemas.completions import CompletionRequest, Completions
from app.utils.lifespan import clients
from app.utils.security import check_api_key

router = APIRouter()


@router.post("/completions")
async def completions(request: CompletionRequest, user: str = Security(check_api_key)) -> Completions:
    """
    Completion API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/completions/create for the API specification.
    """

    request = dict(request)

    client = clients["models"][request["model"]]
    response = client.completions.create(**request)

    return response
