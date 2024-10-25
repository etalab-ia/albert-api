from typing import List, Literal, Optional, Union

from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
)
from pydantic import BaseModel, Field, model_validator

from app.utils.exceptions import ContextLengthExceededException, MaxTokensExceededException, WrongModelTypeException
from app.utils.lifespan import clients
from app.utils.variables import LANGUAGE_MODEL_TYPE


class ChatCompletionRequest(BaseModel):
    # See https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/openai/protocol.py
    messages: List[ChatCompletionMessageParam]
    model: str
    stream: Optional[Literal[True, False]] = False
    frequency_penalty: Optional[float] = 0.0
    max_tokens: Optional[int] = None
    n: Optional[int] = 1
    presence_penalty: Optional[float] = 0.0
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    user: Optional[str] = None
    seed: Optional[int] = None
    stop: Union[Optional[str], List[str]] = Field(default_factory=list)
    user: Optional[str] = None
    best_of: Optional[int] = None
    top_k: int = -1
    min_p: float = 0.0

    class ConfigDict:
        extra = "allow"

    @model_validator(mode="before")
    def validate_model(cls, value):
        if clients.models[value["model"]].type != LANGUAGE_MODEL_TYPE:
            raise WrongModelTypeException()

        if not clients.models[value["model"]].check_context_length(messages=value["messages"]):
            raise ContextLengthExceededException()

        if "max_tokens" in value and value["max_tokens"] is not None and value["max_tokens"] > clients.models[value["model"]].max_context_length:
            raise MaxTokensExceededException()
        return value


class ChatCompletion(ChatCompletion):
    pass


class ChatCompletionChunk(ChatCompletionChunk):
    pass
