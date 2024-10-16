import base64
import hashlib
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.security import User
from app.utils.exceptions import InvalidAPIKeyException, InvalidAuthenticationSchemeException
from app.utils.lifespan import clients
from app.utils.variables import ADMIN_ROLE


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


def check_api_key(
    api_key: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer(scheme_name="API key"))],
) -> str:
    """
    Check if the API key is valid.

    Args:
        api_key (Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer(scheme_name="API key")]): The API key to check.

    Returns:
        str: User ID, corresponding to the encoded API key or "no-auth" if no authentication is set in the configuration file.
    """
    if clients.auth:
        if api_key.scheme != "Bearer":
            raise InvalidAuthenticationSchemeException()

        role = clients.auth.check_api_key(api_key.credentials)
        if role is None:
            raise InvalidAPIKeyException()

        user_id = encode_string(input=api_key.credentials)

    else:
        user_id = "no-auth"
        role = ADMIN_ROLE

    return User(id=user_id, role=role)


def check_rate_limit(request: Request) -> str | None:
    """
    Check the rate limit for the user.

    Args:
        request (Request): The request object.

    Returns:
        str | None: None if the user is admin (no rate limit), the user id otherwise.
    """

    authorization = request.headers.get("Authorization")
    scheme, credentials = authorization.split(" ") if authorization else ("", "")
    api_key = HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)
    user = check_api_key(api_key=api_key)

    if user.role == ADMIN_ROLE:
        return None
    else:
        return user.id
