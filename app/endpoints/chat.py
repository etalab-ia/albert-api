from typing import List, Tuple, Union

from fastapi import APIRouter, Request, Security

from app.clients.internet import BaseInternetClient as InternetClient
from app.clients.search import BaseSearchClient as SearchClient
from app.helpers import ModelRegistry, SearchManager, StreamingResponseWithStatusCode
from app.schemas.chat import ChatCompletion, ChatCompletionChunk, ChatCompletionRequest
from app.schemas.search import Search
from app.schemas.security import User
from app.utils.lifespan import databases, internet, limiter, models
from app.utils.security import check_api_key, check_rate_limit
from app.utils.settings import settings
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS
from app.utils.exceptions import NoVectorStoreAvailableException

router = APIRouter()


@router.post(path=ENDPOINT__CHAT_COMPLETIONS)
@limiter.limit(limit_value=settings.rate_limit.by_user, key_func=lambda request: check_rate_limit(request=request))
async def chat_completions(
    request: Request, body: ChatCompletionRequest, user: User = Security(dependency=check_api_key)
) -> Union[ChatCompletion, ChatCompletionChunk]:
    """Creates a model response for the given chat conversation.

    **Important**: any others parameters are authorized, depending of the model backend. For example, if model is support by vLLM backend, additional
    fields are available (see https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/openai/protocol.py#L209). Similarly, some defined fields
    may be ignored depending on the backend used and the model support.
    """

    # retrieval augmentation generation
    async def retrieval_augmentation_generation(
        body: ChatCompletionRequest, models: ModelRegistry, search: SearchClient, internet: InternetClient
    ) -> Tuple[ChatCompletionRequest, List[Search]]:
        searches = []
        if body.search:
            if not search:
                raise NoVectorStoreAvailableException()
            search_manager = SearchManager(models=models, search=search, internet=internet)
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

    body, searches = await retrieval_augmentation_generation(body=body, models=models.registry, search=databases.search, internet=internet.search)

    # select client
    model = models.registry[body["model"]]
    client = model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)

    # not stream case
    if not body["stream"]:
        response = await client.forward_request(
            method="POST",
            json=body,
            additional_data_value=searches,
            additional_data_key="search_results",
        )
        return ChatCompletion(**response.json())

    # stream case
    return StreamingResponseWithStatusCode(
        content=client.forward_stream(
            method="POST",
            json=body,
            additional_data_value=searches,
            additional_data_key="search_results",
        ),
        media_type="text/event-stream",
    )
