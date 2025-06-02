import json
import time
from typing import Annotated, Dict, List, Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.auth import Limit, LimitType, PermissionType, Role, User
from app.schemas.collections import CollectionVisibility
from app.schemas.core.auth import UserModelLimits
from app.sql.session import get_db as get_session
from app.utils.context import global_context, request_context
from app.utils.exceptions import (
    InsufficientBudgetException,
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
    ENDPOINT__FILES,
    ENDPOINT__OCR,
    ENDPOINT__RERANK,
    ENDPOINT__ROLES_ME,
    ENDPOINT__SEARCH,
    ENDPOINT__TOKENS,
    ENDPOINT__USERS_ME,
)


class AccessController:
    """
    Access controller ensure user access:
    - API key validation
    - rate limiting application (per requests and per tokens)
    - permissions to access the requested resource

    Access controller is used as a dependency of all endpoints.
    """

    def __init__(self, permissions: List[PermissionType] = []):
        self.permissions = permissions

    async def __call__(
        self, 
        request: Request, 
        api_key: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
        session: AsyncSession = Depends(get_session)
    ) -> User:  # fmt: off
        user, role, limits, token_id = await self._check_api_key(api_key=api_key, session=session)

        # invalid token if user is expired, except for /v1/roles/me and /v1/users/me endpoints
        if (
            user.expires_at
            and user.expires_at < time.time()
            and not request.url.path.endswith(ENDPOINT__ROLES_ME)
            and not request.url.path.endswith(ENDPOINT__USERS_ME)
        ):
            raise InvalidAPIKeyException()

        await self._check_permissions(role=role)

        # add authenticated user to request state for logging usages
        context = request_context.get()
        context.user_id = user.id
        context.role_id = role.id
        context.token_id = token_id

        if request.url.path.endswith(ENDPOINT__AUDIO_TRANSCRIPTIONS) and request.method == "POST":
            await self._check_audio_transcription_post(user=user, role=role, limits=limits, request=request)

        if request.url.path.endswith(ENDPOINT__CHAT_COMPLETIONS) and request.method == "POST":
            await self._check_chat_completions_post(user=user, role=role, limits=limits, request=request)

        if request.url.path.startswith(f"/v1{ENDPOINT__COLLECTIONS}") and request.method == "PATCH":
            await self._check_collections_patch(user=user, role=role, limits=limits, request=request)

        if request.url.path.endswith(ENDPOINT__COLLECTIONS) and request.method == "POST":
            await self._check_collections_post(user=user, role=role, limits=limits, request=request)

        if request.url.path.endswith(ENDPOINT__EMBEDDINGS) and request.method == "POST":
            await self._check_embeddings_post(user=user, role=role, limits=limits, request=request)

        if request.url.path.endswith(ENDPOINT__FILES) and request.method == "POST":
            await self._check_files_post(user=user, role=role, limits=limits, request=request)

        if request.url.path.endswith(ENDPOINT__OCR) and request.method == "POST":
            await self._check_ocr_post(user=user, role=role, limits=limits, request=request)

        if request.url.path.endswith(ENDPOINT__RERANK) and request.method == "POST":
            await self._check_rerank_post(user=user, role=role, limits=limits, request=request)

        if request.url.path.endswith(ENDPOINT__SEARCH) and request.method == "POST":
            await self._check_search_post(user=user, role=role, limits=limits, request=request)

        if request.url.path.endswith(ENDPOINT__TOKENS) and request.method == "POST":
            await self._check_tokens_post(user=user, role=role, limits=limits, request=request)

        return user

    def __get_user_limits(self, role: Role) -> Dict[str, UserModelLimits]:
        limits = {}

        for model in global_context.models.models:
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

    async def _check_api_key(self, api_key: HTTPAuthorizationCredentials, session: AsyncSession) -> tuple[User, Role, Dict[str, UserModelLimits]]:
        if api_key.scheme != "Bearer":
            raise InvalidAuthenticationSchemeException()

        if not api_key.credentials:
            raise InvalidAPIKeyException()

        if api_key.credentials == settings.auth.master_key:  # master user can do anything
            limits = [Limit(model=model, type=type, value=None) for model in global_context.models.models for type in LimitType]
            permissions = [permission for permission in PermissionType]

            master_role = Role(id=0, name="master", permissions=permissions, limits=limits)
            master_user = User(id=0, name="master", role=0, expires_at=None, created_at=0, updated_at=0)
            master_limits = self.__get_user_limits(role=master_role)

            return master_user, master_role, master_limits, None

        user_id, token_id = await global_context.iam.check_token(session=session, token=api_key.credentials)
        if not user_id:
            raise InvalidAPIKeyException()

        users = await global_context.iam.get_users(session=session, user_id=user_id)
        user = users[0]

        roles = await global_context.iam.get_roles(session=session, role_id=user.role)
        role = roles[0]

        limits = self.__get_user_limits(role=role)

        return user, role, limits, token_id

    async def _check_permissions(self, role: Role) -> None:
        if self.permissions and not all(perm in role.permissions for perm in self.permissions):
            raise InsufficientPermissionException()

    async def _check_request_limits(self, request: Request, user: User, limits: Dict[str, UserModelLimits], model: Optional[str] = None) -> None:  # fmt: off
        if not model:
            return

        model = global_context.models.aliases.get(model, model)

        if model not in limits:  # unkown model (404 will be raised by the model client)
            return

        if limits[model].rpm == 0 or limits[model].rpd == 0:
            raise InsufficientPermissionException(detail=f"Insufficient permissions to access the model {model}.")

        check = await global_context.limiter.hit(user_id=user.id, model=model, type=LimitType.RPM, value=limits[model].rpm)
        if not check:
            remaining = await global_context.limiter.remaining(user_id=user.id, model=model, type=LimitType.RPM, value=limits[model].rpm)
            raise RateLimitExceeded(detail=f"{str(limits[model].rpm)} requests for {model} per minute exceeded (remaining: {remaining}).")

        check = await global_context.limiter.hit(user_id=user.id, model=model, type=LimitType.RPD, value=limits[model].rpd)
        if not check:
            remaining = await global_context.limiter.remaining(user_id=user.id, model=model, type=LimitType.RPD, value=limits[model].rpd)
            raise RateLimitExceeded(detail=f"{str(limits[model].rpd)} requests for {model} per day exceeded (remaining: {remaining}).")

    async def _check_token_limits(self, request: Request, user: User, limits: Dict[str, UserModelLimits], prompt_tokens: int, model: Optional[str] = None) -> None:  # fmt: off
        if not model or not prompt_tokens:
            return

        model = global_context.models.aliases.get(model, model)

        if model not in limits:  # unkown model (404 will be raised by the model client)
            return

        if limits[model].tpm == 0 or limits[model].tpd == 0:
            raise InsufficientPermissionException(detail=f"Insufficient permissions to access the model {model}.")

        # compute the cost (number of hits) of the request by the number of tokens
        check = await global_context.limiter.hit(user_id=user.id, model=model, type=LimitType.TPM, value=limits[model].tpm, cost=prompt_tokens)

        if not check:
            remaining = await global_context.limiter.remaining(user_id=user.id, model=model, type=LimitType.TPM, value=limits[model].tpm)
            raise RateLimitExceeded(detail=f"{str(limits[model].tpm)} input tokens for {model} per minute exceeded (remaining: {remaining}).")

        check = await global_context.limiter.hit(user_id=user.id, model=model, type=LimitType.TPD, value=limits[model].tpd, cost=prompt_tokens)
        if not check:
            remaining = await global_context.limiter.remaining(user_id=user.id, model=model, type=LimitType.TPD, value=limits[model].tpd)
            raise RateLimitExceeded(detail=f"{str(limits[model].tpd)} input tokens for {model} per day exceeded (remaining: {remaining}).")

    async def _check_budget(self, user: User, model: Optional[str] = None) -> None:
        if not model:
            return

        model = global_context.models.aliases.get(model, model)

        if model not in global_context.models.models:
            return

        model = global_context.models(model=model)
        if model.costs.prompt_tokens == 0 and model.costs.completion_tokens == 0:  # free model
            return

        if user.budget == 0:
            raise InsufficientBudgetException(detail="Insufficient budget.")

    async def _check_audio_transcription_post(self, user: User, role: Role, limits: Dict[str, UserModelLimits], request: Request) -> None:
        form = await request.form()
        form = {key: value for key, value in form.items()} if form else {}

        await self._check_request_limits(request=request, user=user, limits=limits, model=form.get("model"))
        await self._check_budget(user=user, model=form.get("model"))

    async def _check_chat_completions_post(self, user: User, role: Role, limits: Dict[str, UserModelLimits], request: Request) -> None:
        body = await request.body()
        body = json.loads(body) if body else {}

        await self._check_request_limits(request=request, user=user, limits=limits, model=body.get("model"))

        if body.get("search", False):  # count the search request as one request to the search model (embeddings)
            await self._check_request_limits(request=request, user=user, limits=limits, model=global_context.documents.qdrant.model.id)

        prompt_tokens = global_context.tokenizer.get_prompt_tokens(endpoint=ENDPOINT__CHAT_COMPLETIONS, body=body)
        await self._check_token_limits(request=request, user=user, limits=limits, prompt_tokens=prompt_tokens, model=body.get("model"))

        await self._check_budget(user=user, model=body.get("model"))

    async def _check_collections_patch(self, user: User, role: Role, limits: Dict[str, UserModelLimits], request: Request) -> None:
        body = await request.body()
        body = json.loads(body) if body else {}

        if body.get("visibility") == CollectionVisibility.PUBLIC and PermissionType.CREATE_PUBLIC_COLLECTION not in role.permissions:
            raise InsufficientPermissionException("Missing permission to update collection visibility to public.")

    async def _check_collections_post(self, user: User, role: Role, limits: Dict[str, UserModelLimits], request: Request) -> None:
        body = await request.body()
        body = json.loads(body) if body else {}

        if body.get("visibility") == CollectionVisibility.PUBLIC and PermissionType.CREATE_PUBLIC_COLLECTION not in role.permissions:
            raise InsufficientPermissionException("Missing permission to create public collections.")

    async def _check_embeddings_post(self, user: User, role: Role, limits: Dict[str, UserModelLimits], request: Request) -> None:
        body = await request.body()
        body = json.loads(body) if body else {}

        await self._check_request_limits(request=request, user=user, limits=limits, model=body.get("model"))

        prompt_tokens = global_context.tokenizer.get_prompt_tokens(endpoint=ENDPOINT__EMBEDDINGS, body=body)
        await self._check_token_limits(request=request, user=user, limits=limits, prompt_tokens=prompt_tokens, model=body.get("model"))

        await self._check_budget(user=user, model=body.get("model"))

    async def _check_files_post(self, user: User, role: Role, limits: Dict[str, UserModelLimits], request: Request) -> None:
        await self._check_request_limits(request=request, user=user, limits=limits, model=global_context.documents.qdrant.model.id)

        await self._check_budget(user=user, model=global_context.documents.qdrant.model.id)

    async def _check_ocr_post(self, user: User, role: Role, limits: Dict[str, UserModelLimits], request: Request) -> None:
        form = await request.form()
        form = {key: value for key, value in form.items()} if form else {}

        await self._check_request_limits(request=request, user=user, limits=limits, model=form.get("model"))

        prompt_tokens = global_context.tokenizer.get_prompt_tokens(endpoint=ENDPOINT__OCR, body=form)
        await self._check_token_limits(request=request, user=user, limits=limits, prompt_tokens=prompt_tokens, model=form.get("model"))

        await self._check_budget(user=user, model=form.get("model"))

    async def _check_rerank_post(self, user: User, role: Role, limits: Dict[str, UserModelLimits], request: Request) -> None:
        body = await request.body()
        body = json.loads(body) if body else {}

        await self._check_request_limits(request=request, user=user, limits=limits, model=body.get("model"))

        prompt_tokens = global_context.tokenizer.get_prompt_tokens(endpoint=ENDPOINT__RERANK, body=body)
        await self._check_token_limits(request=request, user=user, limits=limits, prompt_tokens=prompt_tokens, model=body.get("model"))

        await self._check_budget(user=user, model=body.get("model"))

    async def _check_search_post(self, user: User, role: Role, limits: Dict[str, UserModelLimits], request: Request) -> None:
        body = await request.body()
        body = json.loads(body) if body else {}

        # count the search request as one request to the search model (embeddings)
        await self._check_request_limits(request=request, user=user, limits=limits, model=global_context.documents.qdrant.model.id)

        prompt_tokens = global_context.tokenizer.get_prompt_tokens(endpoint=ENDPOINT__SEARCH, body=body)
        await self._check_token_limits(
            request=request,
            user=user,
            limits=limits,
            prompt_tokens=prompt_tokens,
            model=global_context.documents.qdrant.model.id,
        )

        await self._check_budget(user=user, model=global_context.documents.qdrant.model.id)

    async def _check_tokens_post(self, user: User, role: Role, limits: Dict[str, UserModelLimits], request: Request) -> None:
        body = await request.body()
        body = json.loads(body) if body else {}

        # if the token is for another user, we don't check the expiration date
        if body.get("user") and PermissionType.CREATE_USER not in role.permissions:
            raise InsufficientPermissionException("Missing permission to create token for another user.")
