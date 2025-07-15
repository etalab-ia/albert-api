import datetime as dt
from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import Field, constr, field_validator

from app.schemas import BaseModel


class PermissionType(str, Enum):
    CREATE_ROLE = "create_role"
    READ_ROLE = "read_role"
    UPDATE_ROLE = "update_role"
    DELETE_ROLE = "delete_role"
    CREATE_USER = "create_user"
    READ_USER = "read_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    CREATE_PUBLIC_COLLECTION = "create_public_collection"
    READ_METRIC = "read_metric"


class LimitType(str, Enum):
    TPM = "tpm"
    TPD = "tpd"
    RPM = "rpm"
    RPD = "rpd"


class Limit(BaseModel):
    model: str = Field(description="Model ID")
    type: LimitType
    value: Optional[int] = Field(default=None, ge=0)


class RoleUpdateRequest(BaseModel):
    name: Optional[constr(strip_whitespace=True, min_length=1)] = Field(default=None, description="The new role name.")
    permissions: Optional[List[PermissionType]] = Field(default=None, description="The new permissions.")
    limits: Optional[List[Limit]] = Field(default=None, description="The new limits.")

    @field_validator("limits", mode="after")
    def check_duplicate_limits(cls, limits):
        keys = set()
        if limits is not None:
            for limit in limits:
                key = (limit.model, limit.type.value)
                if key in keys:
                    raise ValueError(f"Duplicate limit found: ({limit.model}, {limit.type}).")
                keys.add(key)
        return limits


class RolesResponse(BaseModel):
    id: int


class RoleRequest(BaseModel):
    name: constr(strip_whitespace=True, min_length=1)
    permissions: Optional[List[PermissionType]] = []
    limits: List[Limit] = []

    @field_validator("limits", mode="after")
    def check_duplicate_limits(cls, limits):
        keys = set()
        for limit in limits:
            key = (limit.model, limit.type.value)
            if key in keys:
                raise ValueError(f"Duplicate limit found: ({limit.model}, {limit.type}).")
            keys.add(key)

        return limits


class Role(BaseModel):
    object: Literal["role"] = "role"
    id: int
    name: str
    permissions: List[PermissionType]
    limits: List[Limit]
    users: int = 0
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    updated_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))


class Roles(BaseModel):
    object: Literal["list"] = "list"
    data: List[Role]


class UserUpdateRequest(BaseModel):
    name: Optional[constr(strip_whitespace=True, min_length=1)] = Field(default=None, description="The new user name. If None, the user name is not changed.")  # fmt: off
    role: Optional[int] = Field(default=None, description="The new role ID. If None, the user role is not changed.")
    budget: Optional[float] = Field(default=None, description="The new budget. If None, the user will have no budget.")
    expires_at: Optional[int] = Field(default=None, description="The new expiration timestamp. If None, the user will never expire.")

    @field_validator("expires_at", mode="before")
    def must_be_future(cls, expires_at):
        if isinstance(expires_at, int):
            if expires_at <= int(dt.datetime.now(tz=dt.UTC).timestamp()):
                raise ValueError("Wrong timestamp, must be in the future.")

        return expires_at


class UsersResponse(BaseModel):
    id: int


class UserRequest(BaseModel):
    name: constr(strip_whitespace=True, min_length=1) = Field(description="The user name.")
    role: int = Field(description="The role ID.")
    budget: Optional[float] = Field(default=None, description="The budget.")
    expires_at: Optional[int] = Field(default=None, description="The expiration timestamp.")

    @field_validator("expires_at", mode="before")
    def must_be_future(cls, expires_at):
        if isinstance(expires_at, int):
            if expires_at <= int(dt.datetime.now(tz=dt.UTC).timestamp()):
                raise ValueError("Wrong timestamp, must be in the future.")

        return expires_at


class User(BaseModel):
    object: Literal["user"] = "user"
    id: int
    name: str
    role: int
    budget: Optional[float] = None
    expires_at: Optional[int] = None
    created_at: int
    updated_at: int
    email: Optional[str] = None
    sub: Optional[str] = None


class Users(BaseModel):
    object: Literal["list"] = "list"
    data: List[User]


class TokensResponse(BaseModel):
    id: int
    token: str


class TokenRequest(BaseModel):
    name: constr(strip_whitespace=True, min_length=1)
    user: Optional[int] = Field(default=None, description="User ID to create the token for another user (by default, the current user). Required CREATE_USER permission.")  # fmt: off
    expires_at: Optional[int] = Field(None, description="Timestamp in seconds")

    @field_validator("expires_at", mode="before")
    def must_be_future(cls, expires_at):
        if isinstance(expires_at, int):
            if expires_at <= int(dt.datetime.now(tz=dt.UTC).timestamp()):
                raise ValueError("Wrong timestamp, must be in the future.")

        return expires_at


class Token(BaseModel):
    object: Literal["token"] = "token"
    id: int
    name: str
    token: str
    user: int
    expires_at: Optional[int] = None
    created_at: int


class Tokens(BaseModel):
    object: Literal["list"] = "list"
    data: List[Token]
