from datetime import datetime
import json
from typing import Annotated, List

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.auth import LimitType, PermissionType, User
from app.schemas.core.auth import AuthenticatedUser
from app.utils.exceptions import (
    InsufficientPermissionException,
    InvalidAPIKeyException,
    InvalidAuthenticationSchemeException,
    RateLimitExceeded,
)
from app.utils.variables import (
    COLLECTION_TYPE__PUBLIC,
    ENDPOINT__AUDIO_TRANSCRIPTIONS,
    ENDPOINT__CHAT_COMPLETIONS,
    ENDPOINT__COLLECTIONS,
    ENDPOINT__DOCUMENTS,
    ENDPOINT__EMBEDDINGS,
    ENDPOINT__FILES,
    ENDPOINT__RERANK,
    ENDPOINT__SEARCH,
    ROOT_ROLE,
)


class Authorization:
    def __init__(self, permissions: List[PermissionType] = []):
        self.permissions = permissions

    async def __call__(self, request: Request, api_key: Annotated[HTTPAuthorizationCredentials, Depends(dependency=HTTPBearer(scheme_name="API key"))]) -> User:  # fmt: off
        user = await self._check_api_key(api_key=api_key)

        if user.role == ROOT_ROLE:  # root user can do anything
            return user

        await self._check_permissions(user=user)

        if request.url.path.startswith(f"/v1{ENDPOINT__AUDIO_TRANSCRIPTIONS}") and request.method == "POST":
            await self._check_audio_transcription_post(user=user, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__CHAT_COMPLETIONS}") and request.method == "POST":
            await self._check_chat_completions_post(user=user, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__COLLECTIONS}") and request.method == "POST":
            await self._check_collections_post(user=user, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__COLLECTIONS}") and request.method == "DELETE":
            await self._check_collections_delete(user=user, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__DOCUMENTS}") and request.method == "DELETE":
            await self._check_documents_delete(user=user, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__EMBEDDINGS}") and request.method == "POST":
            await self._check_embeddings_post(user=user, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__FILES}") and request.method == "POST":
            await self._check_files_delete(user=user, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__RERANK}") and request.method == "POST":
            await self._check_rerank_post(user=user, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__SEARCH}") and request.method == "POST":
            await self._check_search_post(user=user, request=request)

        return user

    async def _check_api_key(self, api_key: HTTPAuthorizationCredentials) -> AuthenticatedUser:
        if api_key.scheme != "Bearer":
            raise InvalidAuthenticationSchemeException()

        if not api_key.credentials:
            raise InvalidAPIKeyException()

        from app.utils.lifespan import context

        user = await context.auth.check_token(token=api_key.credentials)

        if not user or (user.expires_at is not None and user.expires_at < datetime.now()):
            raise InvalidAPIKeyException()

        return user

    async def _check_permissions(self, user: AuthenticatedUser) -> None:
        if self.permissions and not all(perm in user.permissions for perm in self.permissions):
            raise InsufficientPermissionException()

    async def _check_limits(self, user: AuthenticatedUser, model: str, check_only_access: bool = False) -> None:
        from app.utils.lifespan import context

        if user.limits[model].rpm == 0 or user.limits[model].rpd == 0:
            raise InsufficientPermissionException(detail=f"Insufficient permissions to access the model {model}.")

        if check_only_access:
            return

        check = await context.limiter(user=user, model=model, type=LimitType.RPM)
        if not check:
            raise RateLimitExceeded(detail=f"{str(user.limits[model].rpm)} requests for {model} per minute exceeded.")

        check = await context.limiter(user=user, model=model, type=LimitType.RPD)
        if not check:
            raise RateLimitExceeded(detail=f"{str(user.limits[model].rpd)} requests for {model} per day exceeded.")

    async def _check_audio_transcription_post(self, user: AuthenticatedUser, request: Request) -> None:
        # @TODO: add rate limit check
        pass

    async def _check_chat_completions_post(self, user: AuthenticatedUser, request: Request) -> None:
        from app.utils.lifespan import context

        body = await request.body()
        body = json.loads(body)
        model = context.models.aliases.get(body["model"], body["model"])

        if model not in user.limits:
            return

        await self._check_limits(user=user, model=model)

        # @TODO: add rate limit check for search model

    async def _check_collections_post(self, user: AuthenticatedUser, request: Request) -> None:
        from app.utils.lifespan import context

        body = await request.body()
        body = json.loads(body)
        model = context.models.aliases.get(body["model"], body["model"])

        if model not in user.limits:
            return

        await self._check_limits(user=user, model=model, check_only_access=True)

        print("##################", body)
        if body["type"] == COLLECTION_TYPE__PUBLIC and PermissionType.CREATE_PUBLIC_COLLECTION not in user.permissions:
            raise InsufficientPermissionException()

    async def _check_collections_delete(self, user: AuthenticatedUser, request: Request) -> None:
        from app.utils.lifespan import context

        collection_id = request.path_params["collection"]
        collections = await context.databases.search.get_collections(collection_ids=[collection_id])
        if not collections:
            return

        if collections[0]["type"] == COLLECTION_TYPE__PUBLIC and PermissionType.DELETE_PUBLIC_COLLECTION not in user.permissions:
            raise InsufficientPermissionException()

    async def _check_documents_delete(self, user: AuthenticatedUser, request: Request) -> None:
        from app.utils.lifespan import context

        collection_id = request.path_params["collection"]
        collections = await context.databases.search.get_collections(collection_ids=[collection_id])
        if not collections:
            return

        if collections[0]["type"] == COLLECTION_TYPE__PUBLIC and PermissionType.DELETE_PUBLIC_COLLECTION not in user.permissions:
            raise InsufficientPermissionException()

    async def _check_embeddings_post(self, user: AuthenticatedUser, request: Request) -> None:
        from app.utils.lifespan import context

        body = await request.body()
        body = json.loads(body)
        model = context.models.aliases.get(body["model"], body["model"])

        if model not in user.limits:
            return

        await self._check_limits(user=user, model=model)

    async def _check_files_post(self, user: AuthenticatedUser, request: Request) -> None:
        body = await request.body()
        body = json.loads(body)

        if body["type"] == COLLECTION_TYPE__PUBLIC and PermissionType.CREATE_PUBLIC_COLLECTION not in user.permissions:
            raise InsufficientPermissionException()

    async def _check_rerank_post(self, user: AuthenticatedUser, request: Request) -> None:
        from app.utils.lifespan import context

        body = await request.body()
        body = json.loads(body) if body else {}
        model = context.models.aliases.get(body["model"], body["model"])

        if model and model not in user.limits:
            return

        await self._check_limits(user=user, model=model)

    async def _check_search_post(self, user: AuthenticatedUser, request: Request) -> None:
        # @TODO: add collection model check and rate limit of the model
        pass
