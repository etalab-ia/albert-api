from typing import List
from pydantic import BaseModel, Field
from app.schemas.search import SearchMethod
from typing import Literal, Optional


class MultiAgentsRequest(BaseModel):
    # See https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/openai/protocol.py
    prompt: str
    collections: List
    rff_k: int = Field(default=20, description="k constant in RFF algorithm")
    k: int = Field(gt=0, description="Number of results to return")
    method: Literal[SearchMethod.HYBRID, SearchMethod.LEXICAL, SearchMethod.SEMANTIC] = Field(default=SearchMethod.SEMANTIC)
    score_threshold: Optional[float] = Field(0.0, ge=0.0, le=1.0, description="Score of cosine similarity threshold for filtering results")
    max_tokens: int = Field(default=600, description="Max tokens for the final response")
    max_tokens_intermediate: int = Field(default=400, description="Max tokens for intermediate responses")
    model: str = Field(description="Model used for decision making, intermediate answers crafting and final answer")
