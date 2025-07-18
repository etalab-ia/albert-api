import time
import base64
import json
import hashlib

import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from cryptography.fernet import Fernet
import requests

from ui.backend.login import login, oauth_login
from ui.backend.sql.session import get_session
from .css import css_proconnect
from ui.settings import settings  # Ensure settings is imported
import logging

logger = logging.getLogger(__name__)


def header():
    def get_fernet():
        """
        Initialize Fernet encryption using the OAuth2 encryption key from settings
        """
        try:
            # If the key is "changeme", generate a proper key (same logic as backend)
            if settings.playground.encryption_key == "changeme":
                # Generate a consistent key from the default string for development
                key_bytes = hashlib.sha256("changeme".encode()).digest()
                key = base64.urlsafe_b64encode(key_bytes)
            else:
                # Use the provided key
                key = settings.playground.encryption_key.encode()

            return Fernet(key)
        except Exception as e:
            st.error(f"Failed to initialize encryption: {e}")
            return None

    def call_oauth2_logout(api_token: str, proconnect_token: str = None):
        """
        Call the logout endpoint to properly terminate OAuth2 session

        Args:
            api_token: The API token for authentication
            proconnect_token: Optional ProConnect token for ProConnect logout
        """
        logout_url = f"{settings.playground.api_url}/v1/oauth2/logout"

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

    def authenticate():
        session = next(get_session())

        @st.dialog(title="Login")
        def login_form():
            with st.form(key="login"):  # ProConnect login
                with stylable_container(key="ProConnect", css_styles=css_proconnect):
                    # Determine the API base URL
                    proconnect_login_url = f"{settings.playground.api_url}/v1/oauth2/login"

                    st.markdown(
                        f"""
                        <div style="text-align: center;">
                            <form action="{proconnect_login_url}" method="get" style="display: inline-block;">
                                <button class="proconnect-button">
                                    <span class="proconnect-sr-only">S'identifier avec ProConnect</span>
                                </button>
                            </form>
                            <p>
                                <a
                                    href="https://www.proconnect.gouv.fr/"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    title="Qu'est-ce que ProConnect ? - nouvelle fenêtre"
                                >
                                    Qu'est-ce que ProConnect ?
                                </a>
                            </p>
                            <div style="display: flex; align-items: center; margin: 20px 0;">
                                <hr style="flex: 1; border: none; border-top: 1px solid #ccc;">
                                <span style="margin: 0 15px; color: #666; font-size: 14px;">OU</span>
                                <hr style="flex: 1; border: none; border-top: 1px solid #ccc;">
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                # Traditional login
                user_name = st.text_input(label="Email", type="default", key="user_id", icon=":material/email:")
                user_password = st.text_input(label="Password", type="password", key="password", icon=":material/lock:")

                # Strip input
                user_name = user_name.strip()
                user_password = user_password.strip()

                submit = st.form_submit_button(label="Submit")
                if submit:
                    login(user_name, user_password, session)

        # Access the encrypted token parameter
        encrypted_token = st.query_params.get("encrypted_token", None)

        if st.session_state.get("login_status") is None and encrypted_token:
            # Decrypt the token
            decrypted_data = decrypt_oauth_token(encrypted_token)
            if decrypted_data:
                api_key = st.session_state["api_key"] = decrypted_data.get("app_token")
                api_key_id = st.session_state["api_key_id"] = decrypted_data.get("token_id")
                st.session_state["proconnect_token"] = decrypted_data.get("proconnect_token")
                oauth_login(session, api_key, api_key_id)

        if st.session_state.get("login_status") is None:
            login_form()

    with stylable_container(key="Header", css_styles="button{float: right;}"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Albert playground")

        # Authentication
        authenticate()
        if st.session_state.get("login_status") is None:
            st.stop()

        with col2:
            logout = st.button("Logout")
        if logout:
            # Get stored tokens for logout
            api_token = st.session_state.get("api_key")
            proconnect_token = st.session_state.get("proconnect_token")

            # Call logout endpoint if we have an API token
            if api_token:
                with st.spinner("Déconnexion en cours..."):
                    try:
                        # Call logout endpoint with optional ProConnect token
                        call_oauth2_logout(api_token, proconnect_token)
                    except Exception as e:
                        st.warning(f"Erreur lors de la déconnexion: {e}")

            # Always perform local logout regardless of API result
            st.session_state.pop("login_status", default=None)
            st.session_state.pop("user", default=None)
            st.session_state.pop("api_key", default=None)
            st.session_state.pop("proconnect_token", default=None)  # Clean ProConnect token
            st.cache_data.clear()
            st.rerun()

        if st.session_state.get("user") and st.session_state["user"].role["name"] == "master":
            st.warning("You are logged in as the master user. This is not recommended for production use, please use a regular user instead.")
        if st.session_state.get("user") and st.session_state["user"].user["expires_at"] and st.session_state["user"].user["expires_at"] < int(time.time()):  # fmt: off
            st.warning("**Your account has expired. Please contact support to renew your account.**")
        st.markdown("***")
