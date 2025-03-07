from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.users import User
from app.utils.exceptions import InvalidAPIKeyException, InvalidAuthenticationSchemeException
from app.utils.lifespan import auth


class RateLimit:
    def __init__(self, admin: bool = False):
        self.admin = admin

    async def __call__(self, request: Request, api_key: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer(scheme_name="API key"))]) -> User:
        if api_key.scheme != "Bearer":
            raise InvalidAuthenticationSchemeException()

        user = await auth.manager.check_token(token=api_key.credentials, admin=self.admin)

        if not user:
            raise InvalidAPIKeyException()

        roles = await auth.manager.get_roles(role_id=user.role)
        role = roles[0]

        # TODO: check if the user has a rate limit for the model

        if request.method in ["POST", "PUT"]:
            try:
                body = await request.json()
                model = body.get("model")
            except Exception as e:
                print(e)
                # Handle case where request might not have a JSON body
                pass

        return user
