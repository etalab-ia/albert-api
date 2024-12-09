from typing import List
from pydantic import BaseModel, Field
from app.utils.variables import HYBRID_SEARCH_TYPE, LEXICAL_SEARCH_TYPE, SEMANTIC_SEARCH_TYPE
from typing import Literal, Optional


class MultiAgentsRequest(BaseModel):
    # See https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/openai/protocol.py
    user: str
    prompt: str
    collections: List
    rff_k: int = Field(default=20, description="k constant in RFF algorithm")
    k: int = Field(gt=0, description="Number of results to return")
    method: Literal[HYBRID_SEARCH_TYPE, LEXICAL_SEARCH_TYPE, SEMANTIC_SEARCH_TYPE] = Field(default=SEMANTIC_SEARCH_TYPE)
    score_threshold: Optional[float] = Field(0.0, ge=0.0, le=1.0, description="Score of cosine similarity threshold for filtering results")
    supervisor_model: str
    writers_model: str
