from typing import Annotated
import hashlib
import secrets
import base64
from functools import wraps

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.utils.lifespan import clients


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
):
    """
    Check if the API key is valid.

    Args:
        api_key (Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer(scheme_name="API key")]): The API key to check.

    Returns:
        str: The encoded API key or "no-auth" if no authentication is set in the configuration file.
    """

    if clients["auth"]:
        if api_key.scheme != "Bearer":
            raise HTTPException(status_code=403, detail="Invalid authentication scheme")

        if not clients["auth"].check_api_key(api_key.credentials):
            raise HTTPException(status_code=403, detail="Invalid API key")

        key_id = encode_string(input=api_key.credentials)
    else:
        key_id = "no-auth"

    return key_id


def secure_data(func):
    """
    Decorator to isolate user data (collections) by API key. Collections parameter is prefixed with 
    the encoded API key to avoid a user can access data from another user.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        if kwargs["api_key"] == "no-auth":
            return await func(*args, **kwargs)

        # for request parameters
        if "collection" in kwargs and kwargs["collection"] is not None:
            if not kwargs["collection"].startswith("public-"):
                kwargs["collection"] = f"{kwargs['api_key']}-{kwargs['collection']}"

        if "collections" in kwargs and kwargs["collections"] is not None:
            kwargs["collections"] = [f"{kwargs['api_key']}-{collection}" if not collection.startswith("public-") else collection for collection in kwargs["collections"]]  # fmt: off

        # for request body
        if "request" not in kwargs or kwargs["request"] is None:
            return await func(*args, **kwargs)

        kwargs["request"] = dict(kwargs["request"])
        if "collection" in kwargs["request"] and kwargs["request"]["collection"] is not None:
            if not kwargs["request"]["collection"].startswith("public-"):
                kwargs["request"]["collection"] = f"{kwargs['api_key']}-{kwargs['request']['collection']}"  # fmt: off

        if "collections" in kwargs["request"] and kwargs["request"]["collections"] is not None:
            kwargs["request"]["collections"] = [f"{kwargs['api_key']}-{collection}" if not collection.startswith("public-") else collection for collection in kwargs["request"]["collections"]]  # fmt: off

        return await func(*args, **kwargs)

    return wrapper
