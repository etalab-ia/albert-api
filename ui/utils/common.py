from functools import lru_cache
import time
from typing import List, Literal, Optional

import requests
from settings import Settings
import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from utils.variables import COLLECTION_DISPLAY_ID_INTERNET, MODEL_TYPE_AUDIO, MODEL_TYPE_EMBEDDINGS, MODEL_TYPE_LANGUAGE, MODEL_TYPE_RERANK


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def header(check_api_key: bool = False) -> str:
    def authenticate():
        @st.dialog(title="Login")
        def _login():
            with st.form(key="login"):
                user_id = st.text_input(label="Email", type="default", key="user_id")
                password = st.text_input(label="Password", type="password", key="password")
                submit = st.form_submit_button(label="Submit")
                if submit:
                    response = requests.post(
                        url=f"{settings.api_url}/login",
                        json={"user": user_id, "password": password},
                        headers={"Authorization": f"Bearer {settings.api_key}"},
                    )
                    if response.status_code != 200:
                        st.error("Invalid user or password.")
                        st.stop()
                    else:
                        st.session_state["login_status"] = True
                        st.session_state["user"] = response.json()

                        response = requests.get(
                            url=f"{settings.api_url}/roles/{st.session_state["user"]["role"]}",
                            headers={"Authorization": f"Bearer {settings.api_key}"},
                        )
                        if response.status_code != 200:
                            st.error("Error while retrieving user information...")
                            st.stop()
                        else:
                            st.session_state["user"]["role"] = response.json()

                        time.sleep(0.5)
                        st.rerun()
                else:
                    st.stop()

        login_status = st.session_state.get("login_status")

        if login_status is None:
            _login()

    def _check_api_key():
        API_KEY = st.session_state.get("api_key")
        if API_KEY is None:
            with st.form(key="my_form"):
                API_KEY = st.text_input(label="Please enter your API key", type="password")
                submit = st.form_submit_button(label="Submit")
                if submit:
                    response = requests.get(url=f"{settings.api_url}/health", headers={"Authorization": f"Bearer {API_KEY}"})
                    if response.status_code == 200:
                        st.session_state["api_key"] = API_KEY
                        st.toast("Authentication succeed", icon="✅")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.toast("Please enter a correct API key", icon="❌")
                        st.stop()
                else:
                    st.stop()

        return API_KEY

    with stylable_container(
        key="Header",
        css_styles="""
        button{
            float: right;
            
        }
    """,
    ):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Albert playground")

        # Authentication
        authenticate()
        if check_api_key:
            _check_api_key()
        with col2:
            logout = st.button("Logout")
        if logout:
            st.session_state.pop("login_status", default=None)
            st.session_state.pop("user", default=None)
            st.session_state.pop("api_key", default=None)
            st.cache_data.clear()
            st.rerun()
        st.markdown("***")


@st.cache_data(show_spinner=False, ttl=settings.cache_ttl)
def get_models(api_key: str, type: Optional[Literal[MODEL_TYPE_LANGUAGE, MODEL_TYPE_EMBEDDINGS, MODEL_TYPE_AUDIO, MODEL_TYPE_RERANK]] = None) -> list:
    response = requests.get(url=f"{settings.api_url}/v1/models", headers={"Authorization": f"Bearer {api_key}"})
    assert response.status_code == 200, response.text
    models = response.json()["data"]
    if type is None:
        models = sorted([model["id"] for model in models])
    else:
        models = sorted([model["id"] for model in models if model["type"] == type])

    return models


@st.cache_data(show_spinner="Retrieving data...", ttl=settings.cache_ttl)
def get_collections(api_key: str) -> list:
    response = requests.get(url=f"{settings.api_url}/v1/collections", headers={"Authorization": f"Bearer {api_key}"})
    assert response.status_code == 200, response.text
    collections = response.json()["data"]

    collections = [
        collection
        for collection in collections
        if collection["model"] == settings.documents_embeddings_model or collection["id"] == COLLECTION_DISPLAY_ID_INTERNET
    ]

    return collections


@st.cache_data(show_spinner="Retrieving data...", ttl=settings.cache_ttl)
def get_documents(collection_ids: List[str], api_key: str) -> dict:
    documents = list()
    for collection_id in collection_ids:
        response = requests.get(url=f"{settings.api_url}/v1/documents/{collection_id}", headers={"Authorization": f"Bearer {api_key}"})
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        for document in data:
            document["collection_id"] = collection_id
            documents.append(document)

    return documents


@st.cache_data(show_spinner=False, ttl=settings.cache_ttl)
def get_tokens() -> list:
    response = requests.get(
        url=f"{settings.api_url}/tokens/{st.session_state["user"]["id"]}", headers={"Authorization": f"Bearer {settings.api_key}"}
    )

    return response.json()["data"]


@st.cache_data(show_spinner="Retrieving data...", ttl=settings.cache_ttl)
def get_roles():
    response = requests.get(url=f"{settings.api_url}/roles?offset=0&limit=100", headers={"Authorization": f"Bearer {settings.api_key}"})

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    data = [role for role in data if role["id"] != "root"]

    return data


@st.cache_data(show_spinner="Retrieving data...", ttl=settings.cache_ttl)
def get_users():
    response = requests.get(url=f"{settings.api_url}/users?offset=0&limit=100", headers={"Authorization": f"Bearer {settings.api_key}"})
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    data = [user for user in data if user["role"] != "root"]

    return data


def get_limits(models: list, role: dict) -> dict:
    limits = {}
    for model in models:
        limits[model] = {"tpm": 0, "rpm": 0, "rpd": 0}
        for limit in role["limits"]:
            if limit["model"] == model and limit["type"] == "tpm":
                limits[model]["tpm"] = limit["value"]
            elif limit["model"] == model and limit["type"] == "rpm":
                limits[model]["rpm"] = limit["value"]
            elif limit["model"] == model and limit["type"] == "rpd":
                limits[model]["rpd"] = limit["value"]

    return limits


def check_password(password: str) -> bool:
    if len(password) < 8:
        st.toast("New password must be at least 8 characters long", icon="❌")
        return False
    if not any(char.isupper() for char in password):
        st.toast("New password must contain at least one uppercase letter", icon="❌")
        return False
    if not any(char.islower() for char in password):
        st.toast("New password must contain at least one lowercase letter", icon="❌")
        return False
    if not any(char.isdigit() for char in password):
        st.toast("New password must contain at least one digit", icon="❌")
        return False

    return True
