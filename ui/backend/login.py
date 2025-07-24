import base64
import hashlib
import json
import logging
import secrets
import string
import time

import bcrypt
from cryptography.fernet import Fernet
from pydantic import BaseModel
import requests
from sqlalchemy import insert, select
from sqlalchemy.orm import Session
import streamlit as st

from ui.backend.sql.models import User as UserTable
from ui.configuration import configuration
from ui.variables import ADMIN_PERMISSIONS

logger = logging.getLogger(__name__)


class User(BaseModel):
    id: int
    name: str
    api_key_id: int
    api_key: str
    role: dict
    user: dict


def get_fernet():
    """
    Initialize Fernet encryption using the OAuth2 encryption key from configuration
    """
    try:
        # If the key is "changeme", generate a proper key
        if configuration.playground.encryption_key == "changeme":
            # Generate a consistent key from the default string for development
            key_bytes = hashlib.sha256("changeme".encode()).digest()
            key = base64.urlsafe_b64encode(key_bytes)
        else:
            # Use the provided key - it should be 32 url-safe base64-encoded bytes
            key = configuration.playground.encryption_key.encode()

        return Fernet(key)
    except Exception as e:
        st.error(f"Failed to initialize encryption: {e}")
        return None


def encrypt_playground_data(user_id: int) -> str:
    """
    Encrypt playground data containing user_id into a single token

    Args:
        user_id: The user ID to encrypt

    Returns:
        Base64 encoded encrypted token
    """
    try:
        fernet = get_fernet()
        if not fernet:
            raise Exception("Failed to initialize encryption")

        data = {"user_id": user_id, "timestamp": int(time.time())}

        json_data = json.dumps(data)
        encrypted_data = fernet.encrypt(json_data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    except Exception as e:
        st.error(f"Failed to encrypt playground data: {e}")
        raise


def decrypt_oauth_token(encrypted_token: str) -> dict:
    """
    Decrypt OAuth2 redirect token with TTL validation
    """
    try:
        fernet = get_fernet()
        if not fernet:
            return None

        # Decode from base64
        encrypted_data = base64.urlsafe_b64decode(encrypted_token.encode())

        # Decrypt with TTL (5 minutes = 300 seconds)
        decrypted_data = fernet.decrypt(encrypted_data, ttl=300)

        # Parse JSON
        data = json.loads(decrypted_data.decode())

        return data
    except Exception as e:
        st.warning("Une erreur est survenue lors de l'authentification. Veuillez réessayer.")
        st.error(f"Erreur de déchiffrement: {e}")
        return None


def get_hashed_password(password: str) -> str:
    return bcrypt.hashpw(password=password.encode(encoding="utf-8"), salt=bcrypt.gensalt()).decode(encoding="utf-8")


def check_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password=password.encode(encoding="utf-8"), hashed_password=hashed_password.encode(encoding="utf-8"))


def login(user_name: str, user_password: str, session: Session, oauth2=False) -> dict:
    # master login flow
    if user_name == configuration.playground.auth_master_username:
        response = requests.get(url=f"{configuration.playground.api_url}/users/me", headers={"Authorization": f"Bearer {user_password}"})
        if response.status_code != 404:  # only master get 404 on /users/me
            st.error(response.json()["detail"])
            st.stop()

        response = requests.get(url=f"{configuration.playground.api_url}/v1/models", headers={"Authorization": f"Bearer {user_password}"})
        if response.status_code != 200:
            st.error(response.json()["detail"])
            st.stop()
        models = response.json()["data"]

        limits = []
        for model in models:
            limits.append({"model": model["id"], "type": "tpm", "value": None})
            limits.append({"model": model["id"], "type": "tpd", "value": None})
            limits.append({"model": model["id"], "type": "rpm", "value": None})
            limits.append({"model": model["id"], "type": "rpd", "value": None})

        role = {"object": "role", "id": 0, "name": "master", "default": False, "permissions": ADMIN_PERMISSIONS, "limits": limits}
        user = User(
            id=0,
            name=configuration.playground.auth_master_username,
            api_key=user_password,
            api_key_id=0,
            user={"expires_at": None, "budget": None},
            role=role,
        )

        st.session_state["login_status"] = True
        st.session_state["user"] = user
        st.rerun()

    # basic login flow
    db_user = session.execute(select(UserTable).where(UserTable.name == user_name)).scalar_one_or_none()
    if not db_user:
        st.error("Invalid username or password")
        st.stop()

    if not oauth2 and not check_password(password=user_password, hashed_password=db_user.password):
        st.error("Invalid username or password")
        st.stop()

    # Instead of using db_user.api_key directly, call playground_login endpoint
    try:
        # Encrypt the user ID for the playground_login endpoint
        encrypted_token = encrypt_playground_data(db_user.api_user_id)

        # Call the playground_login endpoint
        playground_login_url = f"{configuration.playground.api_url}/v1/oauth2/playground-login"
        response = requests.get(url=playground_login_url, params={"encrypted_token": encrypted_token}, timeout=10)

        if response.status_code != 200:
            st.error(f"Failed to get API key: {response.json().get('detail', 'Unknown error')}")
            st.stop()

        login_data = response.json()
        api_key = login_data["api_key"]
        api_key_id = login_data["token_id"]

    except Exception as e:
        st.error(f"Authentication failed: {str(e)}")
        st.stop()

    response = requests.get(url=f"{configuration.playground.api_url}/users/me", headers={"Authorization": f"Bearer {api_key}"})
    if response.status_code != 200:
        st.error(response.json()["detail"])
        st.stop()
    user = response.json()

    response = requests.get(url=f"{configuration.playground.api_url}/roles/me", headers={"Authorization": f"Bearer {api_key}"})
    if response.status_code != 200:
        st.error(response.json()["detail"])
        st.stop()
    role = response.json()

    user = User(id=db_user.id, name=db_user.name, api_key_id=api_key_id, api_key=api_key, user=user, role=role)

    st.session_state["login_status"] = True
    st.session_state["user"] = user
    st.rerun()


def generate_random_password(length: int = 16) -> str:
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def oauth_login(session: Session, api_key: str, api_key_id: str):
    """After OAuth2 login, backend will provide api_key and api_key_id in URL parameters and we use it to process the login"""
    response = requests.get(url=f"{configuration.playground.api_url}/users/me", headers={"Authorization": f"Bearer {api_key}"})
    if response.status_code != 200:
        st.error(response.json()["detail"])
        st.stop()
    user = response.json()

    response = requests.get(url=f"{configuration.playground.api_url}/roles/me", headers={"Authorization": f"Bearer {api_key}"})
    if response.status_code != 200:
        st.error(response.json()["detail"])
        st.stop()
    role = response.json()

    db_user = session.execute(select(UserTable).where(UserTable.name == user["name"])).scalar_one_or_none()
    if not db_user:
        session.execute(
            insert(UserTable).values(
                name=user["name"],
                password=get_hashed_password(password=generate_random_password()),
                api_user_id=user["id"],
                api_role_id=role["id"],
                api_key_id=api_key_id,
                api_key=api_key,
            )
        )
        session.commit()
    else:
        session.execute(
            UserTable.__table__.update()
            .where(UserTable.id == db_user.id)
            .values(
                api_key=api_key,
                api_key_id=api_key_id,
                api_user_id=user["id"],
                api_role_id=role["id"],
            )
        )
        session.commit()

    # Clear the URL parameters after processing
    st.query_params.clear()
    login(user["name"], None, session, oauth2=True)


def call_oauth2_logout(api_token: str, proconnect_token: str = None):
    """
    Call the logout endpoint to properly terminate OAuth2 session

    Args:
        api_token: The API token for authentication
        proconnect_token: Optional ProConnect token for ProConnect logout
    """
    logout_url = f"{configuration.playground.api_url}/v1/oauth2/logout"

    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}

    # Prepare payload with optional ProConnect token
    payload = {}
    if proconnect_token:
        payload["proconnect_token"] = proconnect_token

    try:
        response = requests.post(logout_url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("Logout successful")
        else:
            logger.warning(f"Logout endpoint returned status {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to call logout endpoint: {e}")
        raise
