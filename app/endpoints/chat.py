import json
from typing import List, Tuple, Union

from fastapi import APIRouter, HTTPException, Request, Security
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
import httpx

from app.helpers import ClientsManager, InternetManager, SearchManager
from app.schemas.chat import ChatCompletion, ChatCompletionChunk, ChatCompletionRequest
from app.schemas.search import Search
from app.schemas.security import User
from app.schemas.settings import Settings
from app.utils.exceptions import WrongModelTypeException
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit
from app.utils.settings import settings
from app.utils.variables import DEFAULT_TIMEOUT, LANGUAGE_MODEL_TYPE

router = APIRouter()


@router.post(path="/chat/completions")
@limiter.limit(limit_value=settings.rate_limit.by_key, key_func=lambda request: check_rate_limit(request=request))
async def chat_completions(
    request: Request, body: ChatCompletionRequest, user: User = Security(dependency=check_api_key)
) -> Union[ChatCompletion, ChatCompletionChunk]:
    """Completion API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/chat/create for the API specification.
    """

    client = clients.models[body.model]
    if client.type != LANGUAGE_MODEL_TYPE:
        raise WrongModelTypeException()
    body.model = client.id  # replace alias by model id
    url = f"{client.base_url}chat/completions"
    headers = {"Authorization": f"Bearer {client.api_key}"}

    def retrieval_augmentation_generation(
        body: ChatCompletionRequest, clients: ClientsManager, settings: Settings
    ) -> Tuple[ChatCompletionRequest, List[Search]]:
        searches = []
        if body.search:
            search_manager = SearchManager(
                model_clients=clients.models,
                search_client=clients.search,
                internet_manager=InternetManager(
                    model_clients=clients.models,
                    internet_client=clients.internet,
                    default_language_model_id=settings.internet.default_language_model,
                    default_embeddings_model_id=settings.internet.default_embeddings_model,
                ),
            )
            searches = search_manager.query(
                collections=body.search_args.collections,
                prompt=body.messages[-1]["content"],
                method=body.search_args.method,
                k=body.search_args.k,
                rff_k=body.search_args.rff_k,
                user=user,
            )
            if searches:
                body.messages[-1]["content"] = body.search_args.template.format(
                    prompt=body.messages[-1]["content"], chunks="\n".join([search.chunk.content for search in searches])
                )

        body = body.model_dump()
        body.pop("search", None)
        body.pop("search_args", None)

        searches = [search.model_dump() for search in searches]
        return body, searches

    body, searches = await run_in_threadpool(retrieval_augmentation_generation, body, clients, settings)

    # not stream case
    if not body["stream"]:
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as async_client:
                response = await async_client.request(method="POST", url=url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
            data["search_results"] = searches

            return ChatCompletion(**data)
        except Exception as e:
            raise HTTPException(status_code=e.response.status_code, detail=json.loads(e.response.text)["message"])

    # stream case
    async def forward_stream(url: str, headers: dict, request: dict):
        try:
            error = None
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as async_client:
                async with async_client.stream(method="POST", url=url, headers=headers, json=request) as response:
                    if response.status_code >= 400:
                        error = await response.aread().decode()
                    response.raise_for_status()

                    i = 0
                    async for chunk in response.aiter_raw():
                        if i == 0:
                            chunks = chunk.decode(encoding="utf-8").split(sep="\n\n")
                            chunk = json.loads(chunks[0].lstrip("data: "))
                            chunk["search_results"] = searches
                            chunks[0] = f"data: {json.dumps(chunk)}"
                            chunk = "\n\n".join(chunks).encode(encoding="utf-8")
                        i = 1
                        yield chunk

        # @TODO: raise the error instead of forwarding it (raise model )
        except Exception as e:
            error = error if error else {"error": {"type": e.__class__.__name__, "message": str(e), "code": 500}}
            yield f"data: {json.dumps(error)}\n\n".encode(encoding="utf-8")
            yield b"data: [DONE]\n\n"

    return StreamingResponse(content=forward_stream(url=url, headers=headers, request=body), media_type="text/event-stream")
