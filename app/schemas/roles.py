from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class RateLimitRequest(BaseModel):
    model: str = Field(default=".*", description="Regex pattern to match the model ID, by default all models are matched.")
    tpm: Optional[int] = Field(default=None, ge=0)
    rpm: Optional[int] = Field(default=None, ge=0)
    rpd: Optional[int] = Field(default=None, ge=0)

    @field_validator("model", mode="before")
    def strip(cls, model):
        model = model.strip()
        return model


class RateLimit(RateLimitRequest):
    model: str = Field(default=".*", description="Regex pattern to match the model ID, by default all models are matched.")
    tpm: Optional[int] = Field(default=None, ge=0)
    rpm: Optional[int] = Field(default=None, ge=0)
    rpd: Optional[int] = Field(default=None, ge=0)
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    updated_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))


class RoleUpdateRequest(BaseModel):
    role: Optional[str] = None
    default: Optional[bool] = None
    admin: Optional[bool] = None
    limits: Optional[List[RateLimitRequest]] = None


class RoleRequest(BaseModel):
    role: str
    default: bool = False
    admin: bool = False
    limits: Optional[List[RateLimitRequest]] = Field(default=[RateLimitRequest(model=".*", tpm=None, rpm=None, rpd=None)])

    @field_validator("role", mode="before")
    def strip(cls, role):
        if isinstance(role, str):
            role = role.strip()
        return role


class Role(BaseModel):
    object: Literal["role"] = "role"
    id: str
    default: bool
    admin: bool
    limits: List[RateLimit]
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    updated_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))


class Roles(BaseModel):
    object: Literal["list"] = "list"
    data: List[Role]
