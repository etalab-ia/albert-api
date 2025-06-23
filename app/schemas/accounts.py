from typing import List, Literal, Optional

from pydantic import Field

from app.schemas import BaseModel


class AccountUsage(BaseModel):
    """Schema for individual account usage record."""

    id: int
    datetime: int = Field(description="Timestamp in seconds")
    duration: Optional[int] = None
    time_to_first_token: Optional[int] = None
    user_id: Optional[int] = None
    token_id: Optional[int] = None
    endpoint: str
    method: Optional[str] = None
    model: Optional[str] = None
    request_model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[float] = None
    total_tokens: Optional[int] = None
    cost: Optional[float] = None
    status: Optional[int] = None
    kwh_min: Optional[float] = None
    kwh_max: Optional[float] = None
    kgco2eq_min: Optional[float] = None
    kgco2eq_max: Optional[float] = None


class AccountUsageResponse(BaseModel):
    """Schema for list of account usage records."""

    object: Literal["list"] = "list"
    data: List[AccountUsage]
    total: int = Field(description="Total number of records")
    has_more: bool = Field(description="Whether there are more records available")
