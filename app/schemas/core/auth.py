from typing import Dict, List, Optional, Self

from pydantic import BaseModel

from app.schemas.auth import LimitType, PermissionType, Role, User


class Limits(BaseModel):
    tpm: Optional[int] = None
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
            limits[model] = Limits(tpm=0, rpm=0, rpd=0)
            for limit in role.limits:
                if limit.model == model and limit.type == LimitType.TPM:
                    limits[model].tpm = limit.value
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
