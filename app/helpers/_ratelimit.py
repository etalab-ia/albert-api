from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.users import User
from app.utils.exceptions import InvalidAPIKeyException, InvalidAuthenticationSchemeException, InsufficientRightsException
from app.utils.lifespan import context
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS


class RateLimit:
    def __init__(self, admin: bool = False):
        self.admin = admin

    async def __call__(self, request: Request, api_key: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer(scheme_name="API key"))]) -> User:
        if api_key.scheme != "Bearer":
            raise InvalidAuthenticationSchemeException()

        user = await context.auth.check_token(token=api_key.credentials)
        if not user:
            raise InvalidAPIKeyException()

        if self.admin and not user.admin:
            raise InsufficientRightsException()

        # rate limit for chat completions
        # @TODO: extend to other endpoints
        if request.url.path.endswith(ENDPOINT__CHAT_COMPLETIONS):
            body = await request.json()
            await context.limiter(user=user, model=body["model"])

        return user
