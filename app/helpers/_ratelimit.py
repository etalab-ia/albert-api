import json
import traceback
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.users import User
from app.utils.exceptions import InsufficientRightsException, InvalidAPIKeyException, InvalidAuthenticationSchemeException
from app.utils.lifespan import context
from app.utils.logging import logger
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

        # rate limit check
        if request.url.path.endswith(ENDPOINT__CHAT_COMPLETIONS):  # @TODO: extend to other endpoints
            body = await request.body()
            body = json.loads(body) if body else {}

            try:
                await context.limiter(user=user, model=body["model"])
            except Exception:
                logger.error(msg="Error during rate limit check.")
                logger.error(msg=traceback.format_exc())

        return user
