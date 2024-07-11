import sys

from fastapi import APIRouter, HTTPException, Security

sys.path.append("..")
from utils.schemas import CompletionRequest, CompletionResponse
from utils.lifespan import clients
from utils.security import check_api_key


router = APIRouter()


@router.post("/completions")
async def completions(
    request: CompletionRequest, api_key: str = Security(check_api_key)
) -> CompletionResponse:
    """
    Completion API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/completions/create for the API specification.
    """

    request = dict(request)

    client = clients["openai"][request["model"]]
    response = client.completions.create(**request)

    return response
