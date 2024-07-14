from typing import Optional, Literal, List, Union

from pydantic import BaseModel
from openai.types import CreateEmbeddingResponse


class EmbeddingsRequest(BaseModel):
    input: Union[List[int], List[List[int]], str, List[str]]
    model: str
    dimensions: Optional[int] = None
    encoding_format: Optional[Literal["float", "base64"]] = "float"
    user: Optional[str] = None


class EmbeddingResponse(CreateEmbeddingResponse):
    pass
