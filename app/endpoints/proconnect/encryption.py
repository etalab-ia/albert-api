import logging
import base64
import hashlib
import json
import time

from cryptography.fernet import Fernet
from fastapi import HTTPException

from app.utils.configuration import configuration

logger = logging.getLogger(__name__)


def get_fernet():
    """
    Initialize Fernet encryption using the OAuth2 encryption key from configuration
    """
    try:
        # If the key is "changeme", generate a proper key
        if configuration.settings.encryption_key == "changeme":
            logger.warning("Using default encryption key 'changeme'. This is not secure for production.")
            # Generate a consistent key from the default string for development
            key_bytes = hashlib.sha256("changeme".encode()).digest()
            key = base64.urlsafe_b64encode(key_bytes)
        else:
            # Use the provided key - it should be 32 url-safe base64-encoded bytes
            key = configuration.settings.encryption_key.encode()

        return Fernet(key)
    except Exception as e:
        logger.error(f"Failed to initialize Fernet encryption: {e}")
        raise HTTPException(status_code=500, detail="Encryption initialization failed")


def encrypt_redirect_data(app_token: str, token_id: str, proconnect_token: str) -> str:
    """
    Encrypt data for playground :
    * app_token: The application token (ie. API key)
    * token_id: The ID of the token in the database
    * proconnect_token: The ProConnect token for OAuth2 session to be used for logout
    """
    try:
        fernet = get_fernet()
        data = {"app_token": app_token, "token_id": token_id, "proconnect_token": proconnect_token, "timestamp": int(time.time())}

        json_data = json.dumps(data)
        encrypted_data = fernet.encrypt(json_data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    except Exception as e:
        logger.error(f"Failed to encrypt redirect data: {e}")
        raise HTTPException(status_code=500, detail="Encryption failed")


def decrypt_playground_data(encrypted_token: str, ttl: int = 300) -> dict:
    """
    Decrypt redirect data from encrypted token with TTL validation

    Args:
        encrypted_token: The encrypted token to decrypt
        ttl: Time to live in seconds (default 5 minutes)

    Returns:
        Dictionary containing decrypted data
    """
    try:
        fernet = get_fernet()
        encrypted_data = base64.urlsafe_b64decode(encrypted_token.encode())
        decrypted_data = fernet.decrypt(encrypted_data, ttl=ttl)
        data = json.loads(decrypted_data.decode())

        return data
    except Exception as e:
        logger.error(f"Failed to decrypt redirect data: {e}")
        raise HTTPException(status_code=400, detail="Invalid or expired token")
