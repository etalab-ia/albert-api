from typing import Union
import json

import json
from typing import Union, List, Tuple

from fastapi import APIRouter, Request, Security,  HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
import httpx

from app.helpers import Search, SearchClient, InternetClient
from app.schemas.chat import ChatCompletion, ChatCompletionChunk, ChatCompletionRequest
from app.schemas.security import User
from app.utils.settings import settings
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit
from app.utils.variables import DEFAULT_TIMEOUT


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

    async def retrieval_augmentation_generation(body: ChatCompletionRequest, search_client: SearchClient, internet_client: InternetClient) -> Tuple[ChatCompletionRequest, List[Search]]:
        searches = []
        if body.rag:
            searches = Search(
                search_client=search_client,
                internet_client=internet_client
            ).query(
                collections=body.rag_parameters.collections,
                prompt=body.messages[-1]["content"],
                k=body.rag_parameters.k,
                score_threshold=body.rag_parameters.score_threshold,
                user=user,
            )
            if searches:
                body.messages[-1]["content"] = body.rag_parameters.template.format(
                    prompt=body.messages[-1]["content"], chunks="\n".join([search.chunk.content for search in searches]))

        body = body.model_dump()
        body.pop("rag", None)
        body.pop("rag_parameters", None)

        return body, searches

    body, chunks = await run_in_threadpool(retrieval_augmentation_generation(), body, clients.search, clients.internet)

    try:
        # not stream case
        if not body["stream"]:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as async_client:
                response = await async_client.request(method="POST", url=url, headers=headers, json=body)
                response.raise_for_status()
                data = response.json()
                data["chunks"] = chunks
            
                return ChatCompletion(**data)

        # stream case
        async def forward_stream(url: str, headers: dict, request: dict):
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as async_client:
                async with async_client.stream(method="POST", url=url, headers=headers, json=request) as response:
                    response.raise_for_status()
                    i = 0
                    async for chunk in response.aiter_raw():
                        if i == 0:
                            chunks = chunk.decode("utf-8").split("\n\n")
                            chunk = json.loads(chunks[0].lstrip("data: "))
                            chunk["chunks"] = chunks
                            chunks[0] = f"data: {json.dumps(chunk)}"
                            chunk = "\n\n".join(chunks).encode("utf-8")
                            i = 1
                        yield chunk

        return StreamingResponse(content=forward_stream(url=url, headers=headers, request=body), media_type="text/event-stream")


    except Exception as e:
        raise HTTPException(status_code=e.response.status_code, detail=json.loads(e.response.text)["message"])
