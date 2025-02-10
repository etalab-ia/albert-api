from types import SimpleNamespace
from typing import List, Tuple, Union

from fastapi import APIRouter, Request, Security

from app.helpers import SearchManager, StreamingResponseWithStatusCode
from app.schemas.chat import ChatCompletion, ChatCompletionChunk, ChatCompletionRequest
from app.schemas.search import Search
from app.schemas.security import User
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit
from app.utils.settings import settings

router = APIRouter()


@router.post(path="/chat/completions")
@limiter.limit(limit_value=settings.rate_limit.by_user, key_func=lambda request: check_rate_limit(request=request))
async def chat_completions(
    request: Request, body: ChatCompletionRequest, user: User = Security(dependency=check_api_key)
) -> Union[ChatCompletion, ChatCompletionChunk]:
    """Completion API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/chat/create for the API specification.
    """

    # retrieval augmentation generation
    async def retrieval_augmentation_generation(body: ChatCompletionRequest, clients: SimpleNamespace) -> Tuple[ChatCompletionRequest, List[Search]]:
        searches = []
        if body.search:
            search_manager = SearchManager(clients=clients)
            searches = await search_manager.query(
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

    body, searches = await retrieval_augmentation_generation(body=body, clients=clients)

    # select client
    model = clients.models[body["model"]]
    client = model.get_client(endpoint="chat/completions")

    # not stream case
    if not body["stream"]:
        response = await client.forward_request(
            endpoint="chat/completions",
            method="POST",
            json=body,
            additional_data_value=searches,
            additional_data_key="search_results",
        )
        return ChatCompletion(**response.json())

    # stream case
    return StreamingResponseWithStatusCode(
        content=client.forward_stream(
            endpoint="chat/completions",
            method="POST",
            json=body,
            additional_data_value=searches,
            additional_data_key="search_results",
        ),
        media_type="text/event-stream",
    )
