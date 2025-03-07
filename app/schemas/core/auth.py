from typing import Dict, List, Optional

from pydantic import BaseModel

from app.schemas.auth import LimitType, PermissionType, Role, User
from app.utils.settings import settings


class Limits(BaseModel):
    tpm: Optional[int] = None
    rpm: Optional[int] = None
    rpd: Optional[int] = None


class AuthenticatedUser(BaseModel):
    id: int
    user: str
    role: str
    permissions: List[PermissionType]
    limits: Dict[str, Limits]
    expires_at: Optional[int] = None

    @classmethod
    def from_user_and_role(cls, id: str, user: User, role: Role):
        from app.utils.lifespan import context

        # TODO support aliases pattern
        limits = {}
        for model in context.models.models:
            if user.id == settings.auth.root_user:
                limits[model] = Limits(tpm=None, rpm=None, rpd=None)
            else:
                limits[model] = Limits(tpm=0, rpm=0, rpd=0)
                for limit in role.limits:
                    if limit.model == model and limit.type == LimitType.TPM:
                        limits[model].tpm = limit.value
                    elif limit.model == model and limit.type == LimitType.RPM:
                        limits[model].rpm = limit.value
                    elif limit.model == model and limit.type == LimitType.RPD:
                        limits[model].rpd = limit.value

        return cls(id=id, user=user.id, role=role.id, limits=limits, permissions=role.permissions, expires_at=user.expires_at)
