import json
import time
from typing import Annotated, List, Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.auth import Limit, Role, User
from app.schemas.collections import CollectionVisibility
from app.schemas.core.auth import LimitType, PermissionType, UserInfo
from app.utils.exceptions import (
    InsufficientPermissionException,
    InvalidAPIKeyException,
    InvalidAuthenticationSchemeException,
    RateLimitExceeded,
)
from app.utils.settings import settings
from app.utils.variables import (
    ENDPOINT__AUDIO_TRANSCRIPTIONS,
    ENDPOINT__CHAT_COMPLETIONS,
    ENDPOINT__COLLECTIONS,
    ENDPOINT__EMBEDDINGS,
    ENDPOINT__RERANK,
    ENDPOINT__SEARCH,
    ENDPOINT__TOKENS,
)


class Authorization:
    def __init__(self, permissions: List[PermissionType] = []):
        self.permissions = permissions

    async def __call__(self, request: Request, api_key: Annotated[HTTPAuthorizationCredentials, Depends(dependency=HTTPBearer(scheme_name="API key"))]) -> UserInfo:  # fmt: off
        user = await self._check_api_key(api_key=api_key)

        await self._check_permissions(user=user)

        if request.url.path.startswith(f"/v1{ENDPOINT__AUDIO_TRANSCRIPTIONS}") and request.method == "POST":
            await self._check_audio_transcription_post(user=user, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__CHAT_COMPLETIONS}") and request.method == "POST":
            await self._check_chat_completions_post(user=user, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__COLLECTIONS}") and request.method == "POST":
            await self._check_collections_post(user=user, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__EMBEDDINGS}") and request.method == "POST":
            await self._check_embeddings_post(user=user, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__RERANK}") and request.method == "POST":
            await self._check_rerank_post(user=user, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__SEARCH}") and request.method == "POST":
            await self._check_search_post(user=user, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__TOKENS}") and request.method == "POST":
            await self._check_tokens_post(user=user, request=request)

        return user

    async def _check_api_key(self, api_key: HTTPAuthorizationCredentials) -> UserInfo:
        # @TODO: add cache
        if api_key.scheme != "Bearer":
            raise InvalidAuthenticationSchemeException()

        if not api_key.credentials:
            raise InvalidAPIKeyException()

        from app.utils.lifespan import context

        if api_key.credentials == settings.auth.master_key:  # master user can do anything
            master_limits = [Limit(model=model, type=type, value=None) for model in context.models.models for type in LimitType]
            master_permissions = [permission for permission in PermissionType]
            master_role = Role(id=0, name="master", default=False, permissions=master_permissions, limits=master_limits)
            master_user = User(id=0, name="master", role=0, expires_at=None, created_at=0, updated_at=0)

            return UserInfo.build(user=master_user, role=master_role)

        user_id = await context.iam.check_token(token=api_key.credentials)
        if not user_id:
            raise InvalidAPIKeyException()

        users = await context.iam.get_users(user_id=user_id)
        user = users[0]

        if user.expires_at and user.expires_at < time.time():
            raise InvalidAPIKeyException()

        roles = await context.iam.get_roles(role_id=user.role)
        role = roles[0]

        return UserInfo.build(user=user, role=role)

    async def _check_permissions(self, user: UserInfo) -> None:
        if self.permissions and not all(perm in user.permissions for perm in self.permissions):
            raise InsufficientPermissionException()

    async def _check_limits(self, user: UserInfo, model: Optional[str] = None, check_only_access: bool = False) -> None:
        from app.utils.lifespan import context

        if not model:
            return

        model = context.models.aliases.get(model, model)

        if model not in user.limits:
            return

        if user.limits[model].rpm == 0 or user.limits[model].rpd == 0:
            raise InsufficientPermissionException(detail=f"Insufficient permissions to access the model {model}.")

        if check_only_access:
            return

        check = await context.limiter(user_id=user.user_id, model=model, type=LimitType.RPM, value=user.limits[model].rpm)
        if not check:
            raise RateLimitExceeded(detail=f"{str(user.limits[model].rpm)} requests for {model} per minute exceeded.")

        check = await context.limiter(user_id=user.user_id, model=model, type=LimitType.RPD, value=user.limits[model].rpd)
        if not check:
            raise RateLimitExceeded(detail=f"{str(user.limits[model].rpd)} requests for {model} per day exceeded.")

    async def _check_audio_transcription_post(self, user: UserInfo, request: Request) -> None:
        body = await request.body()
        body = json.loads(body)

        await self._check_limits(user=user, model=body.get("model"))

    async def _check_chat_completions_post(self, user: UserInfo, request: Request) -> None:
        body = await request.body()
        body = json.loads(body)

        await self._check_limits(user=user, model=body.get("model"))

        if body.get("search", False):
            await self._check_limits(user=user, model=body.get("search_args", {}).get("model", None))

    async def _check_collections_post(self, user: UserInfo, request: Request) -> None:
        body = await request.body()
        body = json.loads(body)

        if body.get("visibility", CollectionVisibility.PRIVATE) == CollectionVisibility.PUBLIC and PermissionType.CREATE_PUBLIC_COLLECTION not in user.permissions:  # fmt: off
            raise InsufficientPermissionException("Missing permission to create public collections.")

    async def _check_embeddings_post(self, user: UserInfo, request: Request) -> None:
        body = await request.body()
        body = json.loads(body)

        await self._check_limits(user=user, model=body.get("model"))

    async def _check_rerank_post(self, user: UserInfo, request: Request) -> None:
        body = await request.body()
        body = json.loads(body) if body else {}

        await self._check_limits(user=user, model=body.get("model"))

    async def _check_search_post(self, user: UserInfo, request: Request) -> None:
        body = await request.body()
        body = json.loads(body)

        await self._check_limits(user=user, model=body.get("model"))

    async def _check_tokens_post(self, user: UserInfo, request: Request) -> None:
        body = await request.body()
        body = json.loads(body)

        if body.get("user", None) and PermissionType.CREATE_USER not in user.permissions:
            raise InsufficientPermissionException("Missing permission to create token for another user.")
