from app.schemas.tools import ToolOutput
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
    ChatCompletionToolChoiceOptionParam,
    ChatCompletionToolParam,
)
from pydantic import BaseModel, Field
from typing import Dict, List, Literal, Optional, Union


class ChatCompletionRequest(BaseModel):
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


class ChatCompletion(ChatCompletion):
    metadata: Optional[List[Dict[str, ToolOutput]]] = []


class ChatCompletionChunk(ChatCompletionChunk):
    metadata: Optional[List[Dict[str, ToolOutput]]] = []
