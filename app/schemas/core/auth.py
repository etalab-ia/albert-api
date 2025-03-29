from typing import Dict, List, Optional, Self

from pydantic import BaseModel
from enum import Enum
from app.schemas.auth import Role, User, PermissionType, LimitType


class LimitingStrategy(str, Enum):
    MOVING_WINDOW = "moving_window"
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"


class Limits(BaseModel):
    tpm: Optional[int] = None
    tpd: Optional[int] = None
    rpm: Optional[int] = None
    rpd: Optional[int] = None


class UserInfo(BaseModel):
    user_id: int
    role_id: int
    permissions: List[PermissionType]
    limits: Dict[str, Limits]
    expires_at: Optional[int] = None

    @classmethod
    def build(cls, user: User, role: Role) -> Self:
        from app.utils.lifespan import context

        limits = {}
        for model in context.models.models:
            limits[model] = Limits(tpm=0, tpd=0, rpm=0, rpd=0)
            for limit in role.limits:
                if limit.model == model and limit.type == LimitType.TPM:
                    limits[model].tpm = limit.value
                elif limit.model == model and limit.type == LimitType.TPD:
                    limits[model].tpd = limit.value
                elif limit.model == model and limit.type == LimitType.RPM:
                    limits[model].rpm = limit.value
                elif limit.model == model and limit.type == LimitType.RPD:
                    limits[model].rpd = limit.value

        return cls(
            user_id=user.id,
            role_id=role.id,
            permissions=role.permissions,
            limits=limits,
            expires_at=user.expires_at,
        )
