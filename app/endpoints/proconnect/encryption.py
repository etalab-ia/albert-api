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
    Encrypt redirect data into a single token
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
