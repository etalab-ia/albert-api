import base64
import hashlib
from typing import Annotated, Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.security import User
from app.utils.config import settings
from app.utils.exceptions import InvalidAPIKeyException, InvalidAuthenticationSchemeException
from app.utils.lifespan import clients
from app.utils.variables import ROLE_LEVEL_0, ROLE_LEVEL_2


def encode_string(input: str) -> str:
    """
    Generate a 16 length unique code from an input string using salted SHA-256 hashing.

    Args:
        input_string (str): The input string to generate the code from.

    Returns:
        tuple[str, bytes]: A tuple containing the generated code and the salt used.
    """
    hash = hashlib.sha256((input).encode()).digest()
    hash = base64.urlsafe_b64encode(hash).decode()
    # remove special characters and limit length
    hash = "".join(c for c in hash if c.isalnum())[:16].lower()

    return hash


if settings.auth:

    def check_api_key(api_key: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer(scheme_name="API key"))]) -> str:
        """
        Check if the API key is valid.

        Args:
            api_key (Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer(scheme_name="API key")]): The API key to check.

        Returns:
            str: User ID, corresponding to the encoded API key or "no-auth" if no authentication is set in the configuration file.
        """

        if api_key.scheme != "Bearer":
            raise InvalidAuthenticationSchemeException()

        role = clients.auth.check_api_key(api_key.credentials)
        if role is None:
            raise InvalidAPIKeyException()

        user_id = encode_string(input=api_key.credentials)

        return User(id=user_id, role=role)

else:

    def check_api_key(api_key: Optional[str] = None) -> str:
        return User(id="no-auth", role=ROLE_LEVEL_2)


def check_rate_limit(request: Request) -> Optional[str]:
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
    user = check_api_key(api_key=api_key)

    if user.role > ROLE_LEVEL_0:
        return None
    else:
        return user.id
