import json
from typing import Union

from fastapi import APIRouter, HTTPException, Security
from fastapi.responses import StreamingResponse
import httpx

from app.schemas.chat import ChatCompletion, ChatCompletionChunk, ChatCompletionRequest
from app.schemas.config import LANGUAGE_MODEL_TYPE
from app.tools import *
from app.tools import __all__ as tools_list
from app.utils.config import LOGGER
from app.utils.lifespan import clients
from app.utils.security import check_api_key

router = APIRouter()


# @TODO: remove tooling from here
@router.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest, user: str = Security(check_api_key)) -> Union[ChatCompletion, ChatCompletionChunk]:
    """Completion API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/chat/create for the API specification.
    """

    request = dict(request)
    client = clients["models"][request["model"]]
    if client.type != LANGUAGE_MODEL_TYPE:
        raise HTTPException(status_code=400, detail="Model is not a language model")

    url = f"{client.base_url}chat/completions"
    headers = {"Authorization": f"Bearer {client.api_key}"}

    if not client.check_context_length(model=request["model"], messages=request["messages"]):
        raise HTTPException(status_code=400, detail="Context length too large")

    # tool call
    metadata = list()
    tools = request.get("tools")
    if tools:
        for tool in tools:
            if tool["function"]["name"] not in tools_list:
                raise HTTPException(status_code=404, detail="Tool not found")
            func = globals()[tool["function"]["name"]](clients=clients)
            params = request | tool["function"]["parameters"]
            params["user"] = user
            LOGGER.debug(f"params: {params}")
            try:
                tool_output = await func.get_prompt(**params)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"tool error {e}")
            metadata.append({tool["function"]["name"]: tool_output.model_dump()})
            request["messages"] = [{"role": "user", "content": tool_output.prompt}]
        request.pop("tools")

        if not client.check_context_length(model=request["model"], messages=request["messages"]):
            raise HTTPException(status_code=400, detail="Context length too large after tool call")

    # non stream case
    if not request["stream"]:
        async_client = httpx.AsyncClient(timeout=20)
        response = await async_client.request(method="POST", url=url, headers=headers, json=request)
        response.raise_for_status()
        data = response.json()
        data["metadata"] = metadata
        return ChatCompletion(**data)

    # stream case
    async def forward_stream(url: str, headers: dict, request: dict):
        async with httpx.AsyncClient(timeout=20) as async_client:
            async with async_client.stream(method="POST", url=url, headers=headers, json=request) as response:
                i = 0
                async for chunk in response.aiter_raw():
                    if i == 0:
                        chunks = chunk.decode("utf-8").split("\n\n")
                        chunk = json.loads(chunks[0].lstrip("data: "))
                        chunk["metadata"] = metadata
                        chunks[0] = f"data: {json.dumps(chunk)}"
                        chunk = "\n\n".join(chunks).encode("utf-8")
                        i = 1
                    yield chunk

    return StreamingResponse(forward_stream(url, headers, request), media_type="text/event-stream")
