import urllib
from typing import Union, Optional
import uuid
import sys

import yaml
from fastapi import APIRouter, HTTPException, Security
from fastapi.responses import StreamingResponse

sys.path.append("..")
from utils.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    CompletionRequest,
    CompletionResponse,
    EmbeddingsRequest,
    EmbeddingResponse,
    Model,
    ModelResponse,
)
from utils.lifespan import clients
from utils.security import check_api_key
from tools import *
from tools import __all__ as tools_list


router = APIRouter()


@router.get("/models/{model}")
@router.get("/models")
def models(
    model: Optional[str] = None, api_key: str = Security(check_api_key)
) -> Union[ModelResponse, Model]:
    """
    Model API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/models/list for the API specification.
    """
    if model is not None:
        try:
            # support double encoding
            unquote_model = urllib.parse.unquote(urllib.parse.unquote(model))
            client = clients["openai"][unquote_model]
            response = dict([row for row in client.models.list().data if row.id == unquote_model][0])  # fmt: off
        except KeyError:
            raise HTTPException(status_code=404, detail="Model not found.")
    else:
        base_urls = list()
        response = {"object": "list", "data": []}
        for model_id, client in clients["openai"].items():
            if client.base_url not in base_urls:
                base_urls.append(str(client.base_url))
                for row in client.models.list().data:
                    response["data"].append(dict(row))

    return response


@router.post("/completions")
async def completions(
    request: CompletionRequest, api_key: str = Security(check_api_key)
) -> CompletionResponse:
    """
    Completion API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/completions/create for the API specification.
    """

    request = dict(request)

    try:
        client = clients["openai"][request["model"]]
    except KeyError:
        raise HTTPException(status_code=404, detail="Model not found.")
    response = client.completions.create(**request)

    return response


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest, api_key: str = Security(check_api_key)
) -> ChatCompletionResponse:
    """Completion API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/chat/create for the API specification.
    """

    request = dict(request)
    chat_id = request.pop("id")
    client = clients["openai"][request["model"]]

    # tools
    user_message = request["messages"][-1]  # keep user message without tools for chat history
    tools = request.get("tools")
    if tools:
        if not request["user"]:
            raise HTTPException(status_code=403, detail="A user is required to use tools.")
        for tool in tools:
            if tool["function"]["name"] not in tools_list:
                raise HTTPException(status_code=404, detail="Tool not found")
            func = globals()[tool["function"]["name"]](clients=clients, user=request["user"])
            tool_params = tool["function"]["parameters"]
            params = request | tool_params  # priority to tool parameters
            prompt = func.get_rag_prompt(**params)
            request["messages"] = [{"role": "user", "content": prompt}]
        request.pop("tools")

    # retrieve chat history
    if request["user"]:
        if chat_id:
            chat_history = clients["chathistory"].get_chat_history(user_id=request["user"], chat_id=chat_id)  # fmt: off
            if "messages" in chat_history.keys():  # to avoid empty chat history
                request["messages"] = chat_history["messages"] + request["messages"]
        else:
            chat_id = str(uuid.uuid4())

    # non stream case
    if not request["stream"]:
        response = client.chat.completions.create(**request)

        # add messages to chat history
        if request["user"]:
            response.id = chat_id
            clients["chathistory"].add_messages(
                user_id=request["user"],
                chat_id=chat_id,
                user_message=user_message,
                assistant_message={
                    "role": "assistant",
                    "content": response.choices[0].message.content,
                },
            )

        return response

    # stream case
    def get_openai_generator(client, **request):
        content = ["" for n in range(request["n"])]
        stream = client.chat.completions.create(**request)
        for event in stream:
            # capture messages for chat history
            message = event.choices[0].delta.content
            message = "" if message is None else message
            content[event.choices[0].index] = content[event.choices[0].index] + message

            event = dict(event)
            if request["user"]:
                event["id"] = chat_id
            event = str(event).replace("None", "null")

            yield "data: " + event + "\n\n"
        yield "data: [DONE] \n\n"

        # add messages to chat history
        if request["user"]:
            clients["chathistory"].add_messages(
                user_id=request["user"],
                chat_id=chat_id,
                user_message=user_message,
                assistant_message={"role": "assistant", "content": content[0]},
            )

    return StreamingResponse(get_openai_generator(client, **request), media_type="text/event-stream")  # fmt: off


@router.post("/embeddings")
def embeddings(
    request: EmbeddingsRequest, api_key: str = Security(check_api_key)
) -> EmbeddingResponse:
    """
    Embedding API similar to OpenAI's API.
    See https://platform.openai.com/docs/api-reference/embeddings/create for the API specification.
    """

    request = dict(request)
    try:
        client = clients["openai"][request["model"]]
    except KeyError:
        raise HTTPException(status_code=404, detail="Model not found.")
    response = client.embeddings.create(**request)

    return response
