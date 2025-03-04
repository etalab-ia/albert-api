from typing import List, Tuple, Union

from fastapi import APIRouter, Request, Security

from app.helpers import Authorization, StreamingResponseWithStatusCode
from app.schemas.chat import ChatCompletion, ChatCompletionChunk, ChatCompletionRequest
from app.schemas.search import Search
from app.utils.exceptions import CollectionNotFoundException
from app.utils.lifespan import context
from app.utils.settings import settings
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS, ENDPOINT__EMBEDDINGS

router = APIRouter()


@router.post(path=ENDPOINT__CHAT_COMPLETIONS)
async def chat_completions(request: Request, body: ChatCompletionRequest, user: str = Security(dependency=Authorization())) -> Union[ChatCompletion, ChatCompletionChunk]:  # fmt: off
    """Creates a model response for the given chat conversation.

    **Important**: any others parameters are authorized, depending of the model backend. For example, if model is support by vLLM backend, additional
    fields are available (see https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/openai/protocol.py#L209). Similarly, some defined fields
    may be ignored depending on the backend used and the model support.
    """

    # retrieval augmentation generation
    async def retrieval_augmentation_generation(body: ChatCompletionRequest) -> Tuple[ChatCompletionRequest, List[Search]]:
        results = []
        if body.search:
            if not context.documents:
                raise CollectionNotFoundException()

            model = context.models(model=settings.general.documents_model)
            client = model.get_client(endpoint=ENDPOINT__EMBEDDINGS)

            results = await context.documents.search(
                model_client=client,
                collection_ids=body.collections,
                prompt=body.messages[-1]["content"],
                method=body.search_args.method,
                k=body.search_args.k,
                rff_k=body.search_args.rff_k,
                web_search=body.search.args.web_search,
                user_id=user.user_id,
            )
            if results:
                chunks = "\n".join([result.chunk.content for result in results])
                body.messages[-1]["content"] = body.search_args.template.format(prompt=body.messages[-1]["content"], chunks=chunks)

        body = body.model_dump()
        body.pop("search", None)
        body.pop("search_args", None)

        results = [result.model_dump() for result in results]
        return body, results

    body, results = await retrieval_augmentation_generation(body=body)

    # select client
    model = context.models(model=body["model"])
    client = model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)

    # not stream case
    if not body["stream"]:
        response = await client.forward_request(
            method="POST",
            json=body,
            additional_data_value=results,
            additional_data_key="search_results",
        )
        return ChatCompletion(**response.json())

    # stream case
    return StreamingResponseWithStatusCode(
        content=client.forward_stream(
            method="POST",
            json=body,
            additional_data_value=results,
            additional_data_key="search_results",
        ),
        media_type="text/event-stream",
    )
