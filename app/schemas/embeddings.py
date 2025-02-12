from typing import List, Literal, Optional, Union

from openai.types import CreateEmbeddingResponse
from pydantic import BaseModel, Field, field_validator


class OpenAIBaseModel(BaseModel):
    class Config:
        extra = "allow"


class EmbeddingsRequest(OpenAIBaseModel):
    input: Union[List[int], List[List[int]], str, List[str]] = Field(default=..., description="Input text to embed, encoded as a string or array of tokens. To embed multiple inputs in a single request, pass an array of strings or array of token arrays. The input must not exceed the max input tokens for the model (call `/v1/models` endpoint to get the `max_context_length` by model) and cannot be an empty string.")  # fmt: off
    model: str = Field(default=..., description="ID of the model to use. Call `/v1/models` endpoint to get the list of available models, only `text-embeddings-inference` model type is supported.")  # fmt: off
    dimensions: Optional[int] = Field(default=None, description="The number of dimensions the resulting output embeddings should have.")  # fmt: off
    encoding_format: Optional[Literal["float"]] = Field(default="float", description="The format of the output embeddings. Only `float` is supported.")  # fmt: off

    @field_validator("input")
    def validate_input(cls, input):
        assert input, "input must not be an empty string"
        return input


class Embeddings(CreateEmbeddingResponse):
    pass
