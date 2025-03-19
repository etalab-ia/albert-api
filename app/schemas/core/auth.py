from typing import Dict, List, Optional

from pydantic import BaseModel

from app.schemas.auth import LimitType, PermissionType, Role, User
from app.schemas.collections import Collection, CollectionVisibility
from app.utils.settings import settings


class Limits(BaseModel):
    tpm: Optional[int] = None
    rpm: Optional[int] = None
    rpd: Optional[int] = None


class UserInfo(BaseModel):
    id: int
    role_id: int
    permissions: List[PermissionType]
    limits: Dict[str, Limits]
    public_collections: List[int] = []
    private_collections: List[int] = []
    expires_at: Optional[int] = None

    @classmethod
    def build(cls, id: str, user: User, role: Role, collections: List[Collection]):
        from app.utils.lifespan import context

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

        public_collections = []
        private_collections = []
        for collection in collections:
            if collection.type == CollectionVisibility.PUBLIC:
                public_collections.append(collection.id)
            else:
                private_collections.append(collection.id)

        return cls(
            id=id,
            role_id=role.id,
            permissions=role.permissions,
            limits=limits,
            public_collections=public_collections,
            private_collections=private_collections,
            expires_at=user.expires_at,
        )
