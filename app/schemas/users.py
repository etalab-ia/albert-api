from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.roles import Role
from typing import Dict


class BudgetReset(Enum):
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"
    YEAR = "year"


class UserUpdateRequest(BaseModel):
    user: Optional[str] = Field(default=None, description="The new user ID.")
    role: Optional[str] = Field(default=None, description="The new role ID.")
    password: Optional[str] = Field(default=None, description="The new password.")
    budget_allocation: Optional[float] = Field(default=None, description="The new budget allocation.")
    budget_reset: Optional[BudgetReset] = Field(default=None, description="The new budget reset.")

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


class AuthenticatedUser(BaseModel):
    object: Literal["authenticated-user"] = "authenticated-user"
    id: str
    role: str
    admin: bool
    tpm: Dict[str, Optional[int]]
    rpm: Dict[str, Optional[int]]
    rpd: Dict[str, Optional[int]]
    budget_allocation: Optional[float] = None
    budget_reset: Optional[BudgetReset] = None

    @classmethod
    def from_user_and_role(cls, user: User, role: Role):
        from app.utils.lifespan import context
        import re

        # TODO support aliases pattern
        tpm, rpm, rpd = {}, {}, {}
        for model in context.models.models:
            tpm[model] = 0
            rpm[model] = 0
            rpd[model] = 0
            for limit in sorted(role.limits, key=lambda limit: len(limit.model)):
                if bool(re.match(pattern=limit.model, string=model)):
                    tpm[model] = limit.tpm
                    rpm[model] = limit.rpm
                    rpd[model] = limit.rpd

        return cls(
            id=user.id,
            role=role.id,
            admin=role.admin,
            tpm=tpm,
            rpm=rpm,
            rpd=rpd,
            budget_allocation=user.budget_allocation,
            budget_reset=user.budget_reset,
        )
