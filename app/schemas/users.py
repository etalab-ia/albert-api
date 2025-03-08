from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, field_validator

from app.schemas.roles import RateLimit, Role
from app.utils.lifespan import models


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


class AuthenticatedUser(BaseModel):
    object: Literal["authenticated_user"] = "authenticated_user"
    id: str
    role: Role
    budget_allocation: Optional[float] = None
    budget_reset: Optional[BudgetReset] = None
    created_at: int
    updated_at: int

    @property
    def models(self) -> set[str]:
        accepted_models = list(set([limit.model for limit in self.role.limits]))
        if "*" in accepted_models:
            return models.models
        else:
            _models = list()
            for model in accepted_models:
                if model in models.models:
                    _models.append(model)
                if model in models.aliases.keys():
                    model = models.aliases[model]
                    if model not in _models:
                        _models.append(model)

        return _models

    # @property
    # def limits(self, model: str, type: RateLimitType) -> List[RateLimit]:
    #     if model in self.models:

    @classmethod
    def from_user_and_role(cls, user: User, role: Role):
        return cls(
            id=user.id,
            role=role,
            budget_allocation=user.budget_allocation,
            budget_reset=user.budget_reset,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def get_rate_limits_for_model(self, model: str) -> List[RateLimit]:
        """Get all rate limits applicable for a specific model"""
        limits = []
        for limit in self.role.limits:
            if limit.model == model or limit.model == "*":
                limits.append(limit)
        return limits
