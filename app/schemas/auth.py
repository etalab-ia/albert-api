import datetime as dt
from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator

from app.utils.settings import settings
from app.utils.variables import ROOT_ROLE


class PermissionType(Enum):
    CREATE_ROLE = "create_role"
    READ_ROLE = "read_role"
    UPDATE_ROLE = "update_role"
    DELETE_ROLE = "delete_role"
    CREATE_USER = "create_user"
    READ_USER = "read_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    CREATE_TOKEN = "create_token"
    READ_TOKEN = "read_token"
    DELETE_TOKEN = "delete_token"
    CREATE_PRIVATE_COLLECTION = "create_private_collection"
    READ_PRIVATE_COLLECTION = "read_private_collection"
    UPDATE_PRIVATE_COLLECTION = "update_private_collection"
    DELETE_PRIVATE_COLLECTION = "delete_private_collection"
    CREATE_PUBLIC_COLLECTION = "create_public_collection"
    READ_PUBLIC_COLLECTION = "read_public_collection"
    UPDATE_PUBLIC_COLLECTION = "update_public_collection"
    DELETE_PUBLIC_COLLECTION = "delete_public_collection"
    READ_METRIC = "read_metric"


class LimitType(Enum):
    TPM = "tpm"
    RPM = "rpm"
    RPD = "rpd"


class Limit(BaseModel):
    model: str = Field(description="Model ID")
    type: LimitType
    value: Optional[int] = Field(default=None, ge=0)


class RoleUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="The new role name.")
    default: Optional[bool] = Field(default=None, description="Whether this role is the default role.")
    permissions: Optional[List[PermissionType]] = Field(default=None, description="The new permissions.")
    limits: Optional[List[Limit]] = Field(default=None, description="The new limits.")

    @field_validator("name", mode="before")
    def strip_name(cls, name):
        if isinstance(name, str):
            name = name.strip()
        return name

    @field_validator("limits", mode="before")
    def check_duplicate_limits(cls, limits):
        keys = []
        if limits is not None:
            for limit in limits:
                key = (limit["model"], limit["type"])
                if key not in keys:
                    keys.append(key)
                else:
                    raise ValueError(f"Duplicate limit found: ({limit["model"]}, {limit["type"]})")

        return limits


class RoleRequest(BaseModel):
    name: str
    default: bool = False
    permissions: Optional[List[PermissionType]] = []
    limits: List[Limit] = []

    @field_validator("name", mode="before")
    def strip_name(cls, name):
        if isinstance(name, str):
            name = name.strip()
        return name

    @field_validator("limits", mode="before")
    def check_duplicate_limits(cls, limits):
        keys = []
        for limit in limits:
            key = (limit["model"], limit["type"])
            if key not in keys:
                keys.append(key)
            else:
                raise ValueError(f"Duplicate limit found: ({limit["model"]}, {limit["type"]})")

        return limits


class Role(BaseModel):
    object: Literal["role"] = "role"
    id: int
    name: str
    default: bool
    permissions: List[PermissionType]
    limits: List[Limit]
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    updated_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))


class Roles(BaseModel):
    object: Literal["list"] = "list"
    data: List[Role]


class UserUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="The new user name.")
    role: Optional[int] = Field(default=None, description="The new role ID.")
    password: Optional[str] = Field(default=None, description="The new password.")
    expires_at: Optional[int] = Field(default=None, description="The new expiration timestamp.")

    @field_validator("expires_at", mode="before")
    def must_be_future(cls, expires_at):
        if isinstance(expires_at, int):
            if expires_at <= int(dt.datetime.now(tz=dt.UTC).timestamp()):
                raise ValueError("Wrong timestamp, must be in the future.")

        return expires_at

    @field_validator("name", mode="before", check_fields=False)
    def strip_name(cls, name):
        if name is not None:
            name = name.strip()
            if not name:  # empty string
                raise ValueError("Empty string is not allowed.")

        return name

    @field_validator("password", mode="before", check_fields=False)
    def strip_password(cls, password):
        if password is not None:
            password = password.strip()
            if not password:  # empty string
                raise ValueError("Empty string is not allowed.")

        return password

    @field_validator("role", mode="after")
    def check_root(cls, role):
        if role == ROOT_ROLE:
            raise HTTPException(status_code=403, detail="Root role is not allowed to add users.")

        return role


class UserRequest(BaseModel):
    name: str = Field(description="The user name.")
    role: int = Field(description="The role ID.")
    password: str = Field(description="The user password.")
    expires_at: Optional[int] = Field(default=None, description="The expiration timestamp.")

    @field_validator("expires_at", mode="before")
    def must_be_future(cls, expires_at):
        if isinstance(expires_at, int):
            if expires_at <= int(dt.datetime.now(tz=dt.UTC).timestamp()):
                raise ValueError("Wrong timestamp, must be in the future.")

        return expires_at

    @field_validator("name", mode="before")
    def strip_name(cls, name):
        name = name.strip()
        if not name:  # empty string
            raise ValueError("Empty string is not allowed.")

        return name

    @field_validator("password", mode="before")
    def strip_password(cls, password):
        password = password.strip()
        if not password:  # empty string
            raise ValueError("Empty string is not allowed.")

        return password

    @field_validator("role", mode="after")
    def check_root(cls, role):
        if role == ROOT_ROLE:
            raise HTTPException(status_code=403, detail="Root role is not allowed to add users.")

        return role


class User(BaseModel):
    object: Literal["user"] = "user"
    id: int
    name: str
    role: int
    expires_at: Optional[int] = None
    created_at: int
    updated_at: int


class Users(BaseModel):
    object: Literal["list"] = "list"
    data: List[User]


class TokenRequest(BaseModel):
    name: str
    user: int
    expires_at: Optional[int] = Field(None, description="Timestamp in seconds")

    @field_validator("name", mode="before")
    def strip_name(cls, name):
        if isinstance(name, str):
            name = name.strip()

        return name

    @field_validator("expires_at", mode="before")
    def must_be_future(cls, expires_at):
        if isinstance(expires_at, int):
            if expires_at <= int(dt.datetime.now(tz=dt.UTC).timestamp()):
                raise ValueError("Wrong timestamp, must be in the future.")

        return expires_at

    @field_validator("user", mode="after")
    def check_root(cls, user):
        if user == settings.auth.root_user:
            raise HTTPException(status_code=403, detail="Root user cannot have a new token.")

        return user


class Token(BaseModel):
    object: Literal["token"] = "token"
    id: int
    name: str
    expires_at: Optional[int] = None
    created_at: int


class Tokens(BaseModel):
    object: Literal["list"] = "list"
    data: List[Token]


class LoginRequest(BaseModel):
    user_name: str
    user_password: str

    @field_validator("user_name", mode="before")
    def strip(cls, user):
        if isinstance(user, str):
            user = user.strip()

        return user
