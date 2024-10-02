import base64
import hashlib
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.utils.lifespan import clients
from app.schemas.security import User


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
            raise HTTPException(status_code=403, detail="Invalid authentication scheme")

        role = clients.auth.check_api_key(api_key.credentials)

        if role is None:
            raise HTTPException(status_code=403, detail="Invalid API key")

        user_id = encode_string(input=api_key.credentials)

    else:
        user_id = "no-auth"

    return User(id=user_id, role=role)
