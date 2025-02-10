from typing import List, Literal, Optional, Union

from openai.types.chat import ChatCompletion, ChatCompletionChunk, ChatCompletionMessageParam
from pydantic import BaseModel, Field, model_validator, field_validator

from app.schemas.search import SearchArgs, Search


DEFAULT_RAG_TEMPLATE = "Réponds à la question suivante en te basant sur les documents ci-dessous : {prompt}\n\nDocuments :\n{chunks}"


class ChatSearchArgs(SearchArgs):
    template: str = Field(
        description='Template to use for the RAG query. The template must contain "{chunks}" and "{prompt}" placeholders.',
        default=DEFAULT_RAG_TEMPLATE,
    )

    @field_validator("template")
    def validate_template(cls, value):
        if "{chunks}" not in value:
            raise ValueError('template must contain "{chunks}" placeholder')
        if "{prompt}" not in value:
            raise ValueError('template must contain "{prompt}" placeholder')

        return value


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

    class Config:
        extra = "allow"

    # search additionnal fields
    search: bool = False
    search_args: Optional[ChatSearchArgs] = None

    @model_validator(mode="after")
    def validate_model(cls, values):
        if values.search:
            if not values.search_args:
                raise ValueError("search_args is required when search is true")

        return values


class ChatCompletion(ChatCompletion):
    search_results: List[Search] = []


class ChatCompletionChunk(ChatCompletionChunk):
    search_results: List[Search] = []
