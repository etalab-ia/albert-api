import json
import time
from typing import Annotated, Dict, List, Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.auth import Limit, LimitType, PermissionType, Role, User
from app.schemas.collections import CollectionVisibility
from app.schemas.core.auth import UserModelLimits
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
    ENDPOINT__ROLES,
    ENDPOINT__SEARCH,
    ENDPOINT__TOKENS,
    ENDPOINT__USERS,
)


class Authorization:
    def __init__(self, permissions: List[PermissionType] = []):
        self.permissions = permissions

    async def __call__(self, request: Request, api_key: Annotated[HTTPAuthorizationCredentials, Depends(dependency=HTTPBearer(scheme_name="API key"))]) -> User:  # fmt: off
        user, role, limits, token_id = await self._check_api_key(api_key=api_key)

        if not request.url.path.startswith(f"{ENDPOINT__ROLES}/me") and not request.url.path.startswith(f"{ENDPOINT__USERS}/me"):
            # invalid token if user is expired, except for /v1/roles/me and /v1/users/me endpoints
            if user.expires_at and user.expires_at < time.time():
                raise InvalidAPIKeyException()

        await self._check_permissions(role=role)

        if request.url.path.startswith(f"/v1{ENDPOINT__AUDIO_TRANSCRIPTIONS}") and request.method == "POST":
            await self._check_audio_transcription_post(user=user, role=role, limits=limits, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__CHAT_COMPLETIONS}") and request.method == "POST":
            await self._check_chat_completions_post(user=user, role=role, limits=limits, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__COLLECTIONS}") and request.method == "POST":
            await self._check_collections_post(user=user, role=role, limits=limits, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__EMBEDDINGS}") and request.method == "POST":
            await self._check_embeddings_post(user=user, role=role, limits=limits, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__RERANK}") and request.method == "POST":
            await self._check_rerank_post(user=user, role=role, limits=limits, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__SEARCH}") and request.method == "POST":
            await self._check_search_post(user=user, role=role, limits=limits, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__TOKENS}") and request.method == "POST":
            await self._check_tokens_post(user=user, role=role, limits=limits, request=request)

        # add authenticated user to request state for usage logging middleware
        request.app.state.user = user
        request.app.state.token_id = token_id

        return user

    def __get_user_limits(self, role: Role) -> Dict[str, UserModelLimits]:
        limits = {}
        from app.utils.lifespan import context

        for model in context.models.models:
            limits[model] = UserModelLimits()
            for limit in role.limits:
                if limit.model == model and limit.type == LimitType.TPM:
                    limits[model].tpm = limit.value
                elif limit.model == model and limit.type == LimitType.TPD:
                    limits[model].tpd = limit.value
                elif limit.model == model and limit.type == LimitType.RPM:
                    limits[model].rpm = limit.value
                elif limit.model == model and limit.type == LimitType.RPD:
                    limits[model].rpd = limit.value

        return limits

    async def _check_api_key(self, api_key: HTTPAuthorizationCredentials) -> tuple[User, Role, Dict[str, UserModelLimits]]:
        # @TODO: add cache
        if api_key.scheme != "Bearer":
            raise InvalidAuthenticationSchemeException()

        if not api_key.credentials:
            raise InvalidAPIKeyException()

        from app.utils.lifespan import context

        if api_key.credentials == settings.auth.master_key:  # master user can do anything
            limits = [Limit(model=model, type=type, value=None) for model in context.models.models for type in LimitType]
            permissions = [permission for permission in PermissionType]

            master_role = Role(id=0, name="master", default=False, permissions=permissions, limits=limits)
            master_user = User(id=0, name="master", role=0, expires_at=None, created_at=0, updated_at=0)
            master_limits = self.__get_user_limits(role=master_role)

            return master_user, master_role, master_limits, None

        user_id, token_id = await context.iam.check_token(token=api_key.credentials)
        if not user_id:
            raise InvalidAPIKeyException()

        users = await context.iam.get_users(user_id=user_id)
        user = users[0]

        roles = await context.iam.get_roles(role_id=user.role)
        role = roles[0]

        limits = self.__get_user_limits(role=role)

        return user, role, limits, token_id

    async def _check_permissions(self, role: Role) -> None:
        if self.permissions and not all(perm in role.permissions for perm in self.permissions):
            raise InsufficientPermissionException()

    async def _check_limits(self, user: User, limits: Dict[str, UserModelLimits], model: Optional[str] = None, check_only_access: bool = False) -> None:  # fmt: off
        from app.utils.lifespan import context

        if not model:
            return

        model = context.models.aliases.get(model, model)

        if model not in limits:
            return

        if limits[model].rpm == 0 or limits[model].rpd == 0:
            raise InsufficientPermissionException(detail=f"Insufficient permissions to access the model {model}.")

        if check_only_access:
            return

        check = await context.limiter(user_id=user.id, model=model, type=LimitType.RPM, value=limits[model].rpm)
        if not check:
            raise RateLimitExceeded(detail=f"{str(limits[model].rpm)} requests for {model} per minute exceeded.")

        check = await context.limiter(user_id=user.id, model=model, type=LimitType.RPD, value=limits[model].rpd)
        if not check:
            raise RateLimitExceeded(detail=f"{str(limits[model].rpd)} requests for {model} per day exceeded.")

    async def _check_audio_transcription_post(self, user: User, role: Role, limits: Dict[str, UserModelLimits], request: Request) -> None:
        pass
        # @TODO: rate limit consumed stream, how handling this ?

    async def _check_chat_completions_post(self, user: User, role: Role, limits: Dict[str, UserModelLimits], request: Request) -> None:
        body = await request.body()
        body = json.loads(body)

        await self._check_limits(user=user, limits=limits, model=body.get("model"))

        if body.get("search", False):
            await self._check_limits(user=user, limits=limits, model=body.get("search_args", {}).get("model", None))

    async def _check_collections_post(self, user: User, role: Role, limits: Dict[str, UserModelLimits], request: Request) -> None:
        body = await request.body()
        body = json.loads(body)

        if body.get("visibility") == CollectionVisibility.PUBLIC and PermissionType.CREATE_PUBLIC_COLLECTION not in role.permissions:
            raise InsufficientPermissionException("Missing permission to create public collections.")

    async def _check_embeddings_post(self, user: User, role: Role, limits: Dict[str, UserModelLimits], request: Request) -> None:
        body = await request.body()
        body = json.loads(body)

        await self._check_limits(user=user, limits=limits, model=body.get("model"))

    async def _check_rerank_post(self, user: User, role: Role, limits: Dict[str, UserModelLimits], request: Request) -> None:
        body = await request.body()
        body = json.loads(body) if body else {}

        await self._check_limits(user=user, limits=limits, model=body.get("model"))

    async def _check_search_post(self, user: User, role: Role, limits: Dict[str, UserModelLimits], request: Request) -> None:
        body = await request.body()
        body = json.loads(body)

        await self._check_limits(user=user, limits=limits, model=body.get("model"))

    async def _check_tokens_post(self, user: User, role: Role, limits: Dict[str, UserModelLimits], request: Request) -> None:
        body = await request.body()
        body = json.loads(body)

        if body.get("user", None) and PermissionType.CREATE_USER not in role.permissions:
            raise InsufficientPermissionException("Missing permission to create token for another user.")
