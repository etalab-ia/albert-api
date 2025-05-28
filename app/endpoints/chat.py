from typing import List, Tuple, Union

from fastapi import APIRouter, Depends, Request, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers.core import AccessController, StreamingResponseWithStatusCode
from app.schemas.chat import ChatCompletion, ChatCompletionChunk, ChatCompletionRequest
from app.schemas.search import Search, SearchMethod
from app.sql.session import get_db as get_session
from app.utils.context import global_context, request_context
from app.utils.exceptions import CollectionNotFoundException
from app.utils.multiagents import MultiAgents
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS

router = APIRouter()


@router.post(path=ENDPOINT__CHAT_COMPLETIONS, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Union[ChatCompletion, ChatCompletionChunk])  # fmt: off
async def chat_completions(request: Request, body: ChatCompletionRequest, session: AsyncSession = Depends(get_session)) -> Union[JSONResponse, StreamingResponseWithStatusCode]:  # fmt: off
    """Creates a model response for the given chat conversation.

    **Important**: any others parameters are authorized, depending of the model backend. For example, if model is support by vLLM backend, additional
    fields are available (see https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/openai/protocol.py#L209). Similarly, some defined fields
    may be ignored depending on the backend used and the model support.
    """

    # retrieval augmentation generation
    async def retrieval_augmentation_generation(body: ChatCompletionRequest, session: AsyncSession) -> Tuple[ChatCompletionRequest, List[Search]]:
        results = []
        if body.search:
            if not global_context.documents:
                raise CollectionNotFoundException()

            results = await global_context.documents.search(
                session=session,
                collection_ids=body.search_args.collections,
                prompt=body.messages[-1]["content"],
                method=body.search_args.method,
                k=body.search_args.k,
                rff_k=body.search_args.rff_k,
                web_search=body.search_args.web_search,
                user_id=request_context.get().user_id,
            )
            if results:
                if body.search_args.method == SearchMethod.MULTIAGENT:
                    body.messages[-1]["content"] = await MultiAgents.full_multiagents(results, body.messages[-1]["content"])
                else:
                    chunks = "\n".join([result.chunk.content for result in results])
                    body.messages[-1]["content"] = body.search_args.template.format(prompt=body.messages[-1]["content"], chunks=chunks)

        body = body.model_dump()
        body.pop("search", None)
        body.pop("search_args", None)

        results = [result.model_dump() for result in results]

        return body, results

    body, results = await retrieval_augmentation_generation(body=body, session=session)
    additional_data = {"search_results": results} if results else {}

    # select client
    model = global_context.models(model=body["model"])
    client = model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)

    # not stream case
    if not body["stream"]:
        response = await client.forward_request(method="POST", json=body, additional_data=additional_data)
        return JSONResponse(content=response.json(), status_code=response.status_code)

    # stream case
    return StreamingResponseWithStatusCode(
        content=client.forward_stream(method="POST", json=body, additional_data=additional_data),
        media_type="text/event-stream",
    )
