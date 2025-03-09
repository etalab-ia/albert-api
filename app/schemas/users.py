from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, field_validator

from app.schemas.roles import Role
from typing import Dict


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
    object: Literal["authenticated-user"] = "authenticated-user"
    id: str
    role: str
    admin: bool
    tpm: Dict[str, Optional[int]]
    rpm: Dict[str, Optional[int]]
    rpd: Dict[str, Optional[int]]
    budget_allocation: Optional[float] = None
    budget_reset: Optional[BudgetReset] = None

    @property
    def limits(self, model: str) -> tuple[Optional[int], Optional[int], Optional[int]]:
        """
        Get the rate limits (TPM, RPM, RPD) for a specific model. If None, model is not
        ratelimited.

        Args:
            model: The model to get the rate limits for.

        Returns:
            A tuple of TPM, RPM, RPD for the model.
        """
        from app.utils.lifespan import models
        import re

        # TODO support aliases pattern
        tpm, rpm, rpd = 0, 0, 0
        for model in models.models:
            for limit in sorted(self.role.limits, key=lambda limit: len(limit.model)):
                if bool(re.match(pattern=limit.model, string=model)):
                    tpm, rpm, rpd = limit.tpm, limit.rpm, limit.rpd
        return tpm, rpm, rpd

    @classmethod
    def from_user_and_role(cls, user: User, role: Role):
        return cls(
            id=user.id,
            role=role.id,
            admin=role.admin,
            budget_allocation=user.budget_allocation,
            budget_reset=user.budget_reset,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
