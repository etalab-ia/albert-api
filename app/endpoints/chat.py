from typing import List, Tuple, Union

from fastapi import APIRouter, Request, Security
from fastapi.concurrency import run_in_threadpool

from app.helpers import ClientsManager, InternetManager, SearchManager, StreamingResponseWithStatusCode
from app.schemas.chat import ChatCompletion, ChatCompletionChunk, ChatCompletionRequest
from app.schemas.search import Search
from app.schemas.security import User
from app.schemas.settings import Settings
from app.utils.exceptions import WrongModelTypeException
from app.utils.lifespan import clients, limiter
from app.utils.route import forward_request, forward_stream
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

    # retrieval augmentation generation
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
        response = await forward_request(
            url=url,
            method="POST",
            headers=headers,
            json=body,
            timeout=DEFAULT_TIMEOUT,
            additional_data_value=searches,
            additional_data_key="search_results",
        )
        return ChatCompletion(**response.json())

    # stream case
    return StreamingResponseWithStatusCode(
        content=forward_stream(
            url=url,
            method="POST",
            headers=headers,
            json=body,
            timeout=DEFAULT_TIMEOUT,
            additional_data_value=searches,
            additional_data_key="search_results",
        ),
        media_type="text/event-stream",
    )
