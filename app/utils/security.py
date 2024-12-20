from typing import Annotated, Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.security import User
from app.utils.settings import settings
from app.utils.exceptions import InvalidAPIKeyException, InvalidAuthenticationSchemeException, InsufficientRightsException
from app.utils.lifespan import clients
from app.schemas.security import Role


if settings.clients.auth:

    async def check_api_key(api_key: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer(scheme_name="API key"))]) -> User:
        """
        Check if the API key is valid.

        Args:
            api_key (Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer(scheme_name="API key")]): The API key to check.

        Returns:
            User: User object, corresponding to the encoded API key or "no-auth" if no authentication is set in the configuration file.
        """

        if api_key.scheme != "Bearer":
            raise InvalidAuthenticationSchemeException()

        user = await clients.auth.check_api_key(api_key.credentials)
        if user is None:
            raise InvalidAPIKeyException()

        return user

    async def check_admin_api_key(api_key: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer(scheme_name="API key"))]) -> User:
        """
        Check if the API key is valid and if the user has admin rights.

        Args:
            api_key (Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer(scheme_name="API key")]): The API key to check.

        Returns:
            User: User object, corresponding to the encoded API key or "no-auth" if no authentication is set in the configuration file.
        """
        user = await check_api_key(api_key=api_key)
        if user.role != Role.ADMIN:
            raise InsufficientRightsException()

        return user

else:

    def check_admin_api_key(api_key: Optional[str] = None) -> User:
        return User(id="no-auth", role=Role.ADMIN)

    def check_api_key(api_key: Optional[str] = None) -> User:
        return User(id="no-auth", role=Role.ADMIN)


async def check_rate_limit(request: Request) -> Optional[str]:
    """
    Check the rate limit for the user.

    Args:
        request (Request): The request object.

    Returns:
        Optional[str]: user_id if the access level is 0, None otherwise (no rate limit applied).
    """

    authorization = request.headers.get("Authorization")
    scheme, credentials = authorization.split(" ") if authorization else ("", "")
    api_key = HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)
    user = await check_api_key(api_key=api_key)

    if user.role.value > Role.USER.value:
        return None
    else:
        return user.id
