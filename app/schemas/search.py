from typing import List, Optional

from pydantic import BaseModel


class SearchRequest(BaseModel):
    prompt: str
    collections: List[str]
    k: int
    score_threshold: Optional[float] = None
