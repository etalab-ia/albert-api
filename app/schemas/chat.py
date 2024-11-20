from typing import List, Literal, Optional, Union

from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
)
from pydantic import BaseModel, Field, model_validator

from app.schemas.chunks import Chunk
from app.schemas.search import RagParameters
from app.utils.exceptions import WrongModelTypeException
from app.utils.lifespan import clients
from app.utils.variables import DEFAULT_RAG_TEMPLATE, LANGUAGE_MODEL_TYPE


class ChatRagParameters(RagParameters):
    template: str = Field(description="Template to use for the RAG query", default=DEFAULT_RAG_TEMPLATE)


class ChatCompletionRequest(BaseModel):
    # see https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/openai/protocol.py
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

    # albert additionnal fields
    rag: bool = False
    rag_parameters: ChatRagParameters = Field(default_factory=ChatRagParameters)

    @model_validator(mode="after")
    def validate_model(cls, values):
        if clients.models[values.model].type != LANGUAGE_MODEL_TYPE:
            raise WrongModelTypeException()

        return values


class ChatCompletion(ChatCompletion):
    chunks: List[Chunk] = []


class ChatCompletionChunk(ChatCompletionChunk):
    chunks: List[Chunk] = []
