from typing import Annotated, Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.clients import AuthenticationClient
from app.schemas.security import Role, User
from app.utils.exceptions import InsufficientRightsException, InvalidAPIKeyException, InvalidAuthenticationSchemeException
from app.utils.lifespan import databases
from app.utils.settings import settings

if settings.databases.grist:

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

        user = await databases.auth.check_api_key(api_key.credentials)
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


def check_rate_limit(request: Request) -> Optional[str]:
    """
    Check the rate limit for the user.

    Args:
        request (Request): The request object.

    Returns:
        Optional[str]: user_id if the access level is 0, None otherwise (no rate limit applied).
    """

    # @TODO: add a middleware to check the key and forward user role to the request
    authorization = request.headers.get("Authorization")
    scheme, credentials = authorization.split(" ") if authorization else ("", "")
    api_key = HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)
    user_id = AuthenticationClient.api_key_to_user_id(input=api_key.credentials)

    return user_id
