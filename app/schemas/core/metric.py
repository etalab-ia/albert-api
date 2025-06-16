from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas import BaseModel

class Metric(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now())
    time_to_first_token_us: Optional[int] = None
    latency_ms: Optional[int] = None
    model_name: str = ""
    api_url: str = ""
