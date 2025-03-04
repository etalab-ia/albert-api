from typing import Literal, List, Optional

from pydantic import BaseModel, field_validator
from enum import Enum


class BudgetReset(Enum):
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"
    YEAR = "year"


class UserUpdateRequest(BaseModel):
    id: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    budget_allocation: Optional[float] = None
    budget_reset: Optional[BudgetReset] = None

    @field_validator("user", mode="after", check_fields=False)
    def strip_user(cls, user):
        if user is not None:
            user = user.strip()
            if not user:  # empty string
                raise ValueError("Empty string is not allowed.")

            return user

    @field_validator("password", mode="after", check_fields=False)
    def strip_password(cls, password):
        if password is not None:
            password = password.strip()
            if not password:  # empty string
                raise ValueError("Empty string is not allowed.")

        return password


class UserRequest(BaseModel):
    user: str
    role: str
    password: str
    budget_allocation: Optional[float] = None
    budget_reset: Optional[BudgetReset] = None

    @field_validator("user", mode="after")
    def strip_user(cls, user):
        user = user.strip()
        if not user:  # empty string
            raise ValueError("Empty string is not allowed.")

        return user

    @field_validator("password", mode="after")
    def strip_password(cls, password):
        password = password.strip()
        if not password:  # empty string
            raise ValueError("Empty string is not allowed.")

        return password


class User(BaseModel):
    object: Literal["user"] = "user"
    id: str
    role: str
    budget_allocation: Optional[float] = None
    budget_reset: Optional[BudgetReset] = None
    created_at: int
    updated_at: int


class Users(BaseModel):
    object: Literal["list"] = "list"
    data: List[User]
