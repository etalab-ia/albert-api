from typing import List, Literal, Optional, Union

from openai.types import CreateEmbeddingResponse
from pydantic import BaseModel, field_validator


class EmbeddingsRequest(BaseModel):
    input: Union[List[int], List[List[int]], str, List[str]]
    model: str
    dimensions: Optional[int] = None
    encoding_format: Optional[Literal["float"]] = "float"
    user: Optional[str] = None

    @field_validator("input")
    def validate_input(cls, input):
        assert input, "input must not be an empty string"
        return input


class Embeddings(CreateEmbeddingResponse):
    pass
