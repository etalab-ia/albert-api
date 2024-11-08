from typing import Union
import json
from fastapi import APIRouter, Request, Security, HTTPException
from fastapi.responses import StreamingResponse
import httpx

from app.schemas.chat import ChatCompletion, ChatCompletionChunk, ChatCompletionRequest
from app.schemas.security import User
from app.utils.settings import settings
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit
from app.utils.variables import DEFAULT_TIMEOUT
from app.helpers import Search

router = APIRouter()


@router.post(path="/chat/completions")
@limiter.limit(limit_value=settings.default_rate_limit, key_func=lambda request: check_rate_limit(request=request))
async def chat_completions(
    request: Request, body: ChatCompletionRequest, user: User = Security(dependency=check_api_key)
) -> Union[ChatCompletion, ChatCompletionChunk]:
    """Completion API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/chat/create for the API specification.
    """
    client = clients.models[body.model]
    url = f"{client.base_url}chat/completions"
    headers = {"Authorization": f"Bearer {client.api_key}"}

    # RAG case
    if body.rag:
        searches = Search(
            engine_client=clients.search,
            internet_client=clients.internet,
        ).query(
            collections=body.rag_parameters.collections,
            prompt=body.messages[-1]["content"],
            k=body.rag_parameters.k,
            score_threshold=body.rag_parameters.score_threshold,
            user=user,
        )
        if searches:
            body.messages[-1]["content"] = body.rag_parameters.template.format(
                prompt=body.messages[-1]["content"], chunks="\n".join([search.chunk.content for search in searches])
            )

    # remove additional fields
    body = body.model_dump()
    body.pop("rag", None)
    body.pop("rag_parameters", None)

    try:
        # not stream case
        if not body["stream"]:
            async with httpx.AsyncClient(timeout=20) as async_client:
                response = await async_client.request(method="POST", url=url, headers=headers, json=body)
                response.raise_for_status()
                data = response.json()
                return ChatCompletion(**data)

        # stream case
        async def forward_stream(url: str, headers: dict, request: dict):
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as async_client:
                async with async_client.stream(method="POST", url=url, headers=headers, json=request) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_raw():
                        yield chunk

        return StreamingResponse(forward_stream(url=url, headers=headers, request=body), media_type="text/event-stream")

    except Exception as e:
        raise HTTPException(status_code=e.response.status_code, detail=json.loads(e.response.text)["message"])
