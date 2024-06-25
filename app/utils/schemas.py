from typing import Optional, Literal, List, Union, Dict, Iterable
from typing_extensions import TypedDict
from uuid import UUID

from pydantic import BaseModel, RootModel, Field
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletion,
    ChatCompletionToolChoiceOptionParam,
    ChatCompletionToolParam,
)
from openai.types import Model, CreateEmbeddingResponse, Completion


class CompletionRequest(BaseModel):
    prompt: Union[str, List[str], Iterable[int], Iterable[Iterable[int]]]
    model: str
    best_of: Optional[int] = None
    echo: Optional[bool] = False
    frequency_penalty: Optional[float] = 0.0
    logit_bias: Optional[Dict[str, float]] = None
    logprobs: Optional[int] = None
    max_tokens: Optional[int] = 16
    n: Optional[int] = 1
    presence_penalty: Optional[float] = 0.0
    seed: Optional[int] = None
    stop: Optional[Union[str, List[str]]] = Field(default_factory=list)
    stream: Optional[bool] = False
    suffix: Optional[str] = None
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    user: Optional[str] = None


class CompletionResponse(Completion):
    pass


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

    # albert additionnal params
    id: Optional[str] = None


class ChatCompletionResponse(ChatCompletion):
    pass


class EmbeddingsRequest(BaseModel):
    input: Union[List[int], List[List[int]], str, List[str]]
    model: str
    dimensions: Optional[int] = None
    encoding_format: Optional[Literal["float", "base64"]] = "float"
    user: Optional[str] = None


class EmbeddingResponse(CreateEmbeddingResponse):
    pass


class ModelResponse(BaseModel):
    object: Literal["list"]
    data: List[Model]


class ChatHistory(BaseModel):
    created: int
    messages: List[ChatCompletionMessageParam]


class ChatHistoryResponse(RootModel):
    root: Dict[UUID, ChatHistory]


class Tool(BaseModel):
    id: str
    description: str
    object: Literal["tool"]


class ToolResponse(BaseModel):
    object: Literal["list"]
    data: List[Tool]


class File(BaseModel):
    object: Literal["file"]
    id: UUID
    bytes: int
    filename: str
    created_at: int


class FileResponse(BaseModel):
    object: Literal["list"]
    data: List[File]


class FileUpload(BaseModel):
    object: Literal["upload"]
    id: UUID
    filename: str
    status: Literal["success", "failed"]


class FileUploadResponse(BaseModel):
    object: Literal["list"]
    data: List[FileUpload]


class Collection(BaseModel):
    object: Literal["collection"]
    name: str
    type: Literal["public", "user"]


class CollectionResponse(BaseModel):
    object: Literal["list"]
    data: List[Collection]
