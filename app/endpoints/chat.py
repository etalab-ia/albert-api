from typing import List, Tuple, Union

from fastapi import APIRouter, Request, Security, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._accesscontroller import AccessController
from app.helpers._streamingresponsewithstatuscode import StreamingResponseWithStatusCode

from app.schemas.chat import ChatCompletion, ChatCompletionChunk, ChatCompletionRequest
from app.schemas.search import Search, SearchMethod
from app.sql.session import get_db_session
from app.utils.context import global_context, request_context
from app.utils.exceptions import CollectionNotFoundException
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS

router = APIRouter()


@router.post(path=ENDPOINT__CHAT_COMPLETIONS, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Union[ChatCompletion, ChatCompletionChunk])  # fmt: off
async def chat_completions(request: Request, body: ChatCompletionRequest, session: AsyncSession = Depends(get_db_session)) -> Union[JSONResponse, StreamingResponseWithStatusCode]:  # fmt: off
    """Creates a model response for the given chat conversation.

    **Important**: any others parameters are authorized, depending on the model backend. For example, if model is support by vLLM backend, additional
    fields are available (see https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/openai/protocol.py#L209). Similarly, some defined fields
    may be ignored depending on the backend used and the model support.
    """

    # retrieval augmentation generation
    async def retrieval_augmentation_generation(
        initial_body: ChatCompletionRequest, inner_session: AsyncSession
    ) -> Tuple[ChatCompletionRequest, List[Search]]:
        results = []
        if initial_body.search:
            if not global_context.document_manager:
                raise CollectionNotFoundException()

            results = await global_context.document_manager.search_chunks(
                session=inner_session,
                collection_ids=initial_body.search_args.collections,
                prompt=initial_body.messages[-1]["content"],
                method=initial_body.search_args.method,
                k=initial_body.search_args.k,
                rff_k=initial_body.search_args.rff_k,
                web_search=initial_body.search_args.web_search,
                user_id=request_context.get().user_id,
            )
            if results:
                if initial_body.search_args.method == SearchMethod.MULTIAGENT:
                    initial_body.messages[-1]["content"] = await global_context.document_manager.multi_agent_manager.full_multiagents(
                        results, initial_body.messages[-1]["content"]
                    )
                else:
                    chunks = "\n".join([result.chunk.content for result in results])
                    initial_body.messages[-1]["content"] = initial_body.search_args.template.format(
                        prompt=initial_body.messages[-1]["content"], chunks=chunks
                    )

        new_body = initial_body.model_dump()
        new_body.pop("search", None)
        new_body.pop("search_args", None)

        results = [result.model_dump() for result in results]

        return new_body, results

    body, results = await retrieval_augmentation_generation(initial_body=body, inner_session=session)
    additional_data = {"search_results": results} if results else {}

    async def handler(client):
        # not stream case
        if not body["stream"]:
            response = await client.forward_request(method="POST", json=body, additional_data=additional_data)
            return JSONResponse(content=response.json(), status_code=response.status_code)

        # stream case
        return StreamingResponseWithStatusCode(
            content=client.forward_stream(method="POST", json=body, additional_data=additional_data),
            media_type="text/event-stream",
        )

    return await global_context.model_registry.execute_request(
        router=body['model'],
        endpoint=ENDPOINT__CHAT_COMPLETIONS,
        handler=handler
    )
