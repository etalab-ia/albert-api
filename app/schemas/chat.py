from typing import List, Literal, Optional, Union

from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
    ChatCompletionToolChoiceOptionParam,
    ChatCompletionToolParam,
)
from pydantic import BaseModel, Field


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
    tool_choice: Optional[Union[Literal["none"], ChatCompletionToolChoiceOptionParam]] = "none"
    tools: List[ChatCompletionToolParam] = None
    user: Optional[str] = None
    best_of: Optional[int] = None
    top_k: int = -1
    min_p: float = 0.0

    class ConfigDict:
        extra = "allow"


class ChatCompletion(ChatCompletion):
    pass


class ChatCompletionChunk(ChatCompletionChunk):
    pass
