from openai.types import CreateEmbeddingResponse
from pydantic import BaseModel
from typing import List, Literal, Optional, Union


class EmbeddingsRequest(BaseModel):
    input: Union[List[int], List[List[int]], str, List[str]]
    model: str
    dimensions: Optional[int] = None
    encoding_format: Optional[Literal["float", "base64"]] = "float"
    user: Optional[str] = None


class Embeddings(CreateEmbeddingResponse):
    pass
