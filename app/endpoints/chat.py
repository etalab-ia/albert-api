from typing import Union

from fastapi import APIRouter, Security
from fastapi.responses import StreamingResponse
import httpx

from app.schemas.chat import ChatCompletion, ChatCompletionChunk, ChatCompletionRequest
from app.schemas.security import User
from app.utils.lifespan import clients
from app.utils.security import check_api_key
from app.utils.variables import LANGUAGE_MODEL_TYPE
from app.utils.exceptions import WrongModelTypeException, ContextLengthExceededException

router = APIRouter()


@router.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest, user: User = Security(check_api_key)) -> Union[ChatCompletion, ChatCompletionChunk]:
    """Completion API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/chat/create for the API specification.
    """

    request = dict(request)
    client = clients.models[request["model"]]
    if client.type != LANGUAGE_MODEL_TYPE:
        raise WrongModelTypeException()

    url = f"{client.base_url}chat/completions"
    headers = {"Authorization": f"Bearer {client.api_key}"}

    if not client.check_context_length(model=request["model"], messages=request["messages"]):
        raise ContextLengthExceededException()

    # non stream case
    if not request["stream"]:
        async with httpx.AsyncClient(timeout=20) as async_client:
            response = await async_client.request(method="POST", url=url, headers=headers, json=request)
            response.raise_for_status()

            data = response.json()
            return ChatCompletion(**data)

    # stream case
    async def forward_stream(url: str, headers: dict, request: dict):
        async with httpx.AsyncClient(timeout=20) as async_client:
            async with async_client.stream(method="POST", url=url, headers=headers, json=request) as response:
                async for chunk in response.aiter_raw():
                    yield chunk

    return StreamingResponse(forward_stream(url, headers, request), media_type="text/event-stream")
