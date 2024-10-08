from typing import List, Literal, Optional, Union

from openai.types import CreateEmbeddingResponse
from pydantic import BaseModel


class EmbeddingsRequest(BaseModel):
    input: Union[List[int], List[List[int]], str, List[str]]
    model: str
    dimensions: Optional[int] = None
    encoding_format: Optional[Literal["float"]] = "float"
    user: Optional[str] = None


class Embeddings(CreateEmbeddingResponse):
    pass
