from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class RateLimitType(Enum):
    RPD = "rpd"  # request per day
    RPM = "rpm"  # request per minute
    TPM = "tpm"  # token per minute


class RateLimitRequest(BaseModel):
    model: str
    type: Optional[RateLimitType] = None
    value: Optional[str] = None


class RateLimit(RateLimitRequest):
    model: str
    type: Optional[RateLimitType] = None
    value: Optional[str] = None
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
    limits: Optional[List[RateLimitRequest]] = Field(
        default=[  # by default allow all access without rate
            RateLimitRequest(model="*", type=RateLimitType.RPD, value=None),
            RateLimitRequest(model="*", type=RateLimitType.RPM, value=None),
            RateLimitRequest(model="*", type=RateLimitType.TPM, value=None),
        ]
    )

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
