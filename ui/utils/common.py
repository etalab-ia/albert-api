from functools import lru_cache
from typing import List, Literal

import requests
from settings import Settings
import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from utils.variables import (
    COLLECTION_DISPLAY_ID_INTERNET,
    MODEL_TYPE_AUDIO,
    MODEL_TYPE_EMBEDDINGS,
    MODEL_TYPE_LANGUAGE,
    MODEL_TYPE_RERANK,
)
import time


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def header() -> str:
    def check_api_key(base_url: str, api_key: str) -> bool:
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(url=base_url.replace("/v1", "/health"), headers=headers)

        return response.status_code == 200

    def authenticate():
        @st.dialog(title="Login")
        def login():
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
            login()

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
        API_KEY = authenticate()
        with col2:
            logout = st.button("Logout")
        if logout:
            st.session_state.pop("login_status")
            st.session_state.pop("user")
            st.rerun()
        st.markdown("***")

    return API_KEY


def clear_cache() -> None:
    get_models.clear()
    get_collections.clear()
    get_documents.clear()
    get_tokens.clear()


@st.cache_data(show_spinner=False, ttl=settings.cache_ttl)
def get_models(type: Literal[MODEL_TYPE_LANGUAGE, MODEL_TYPE_EMBEDDINGS, MODEL_TYPE_AUDIO, MODEL_TYPE_RERANK]) -> tuple[str, str, str]:
    response = requests.get(url=f"{settings.api_url}/v1/models", headers={"Authorization": f"Bearer {settings.api_key}"})
    assert response.status_code == 200, response.text
    models = response.json()["data"]
    models = sorted([model["id"] for model in models if model["type"] == type])

    return models


@st.cache_data(show_spinner="Retrieving data...", ttl=settings.cache_ttl)
def get_collections() -> list:
    response = requests.get(url=f"{settings.api_url}/v1/collections", headers={"Authorization": f"Bearer {settings.api_key}"})
    assert response.status_code == 200, response.text
    collections = response.json()["data"]

    collections = [
        collection
        for collection in collections
        if collection["model"] == settings.documents_embeddings_model or collection["id"] == COLLECTION_DISPLAY_ID_INTERNET
    ]

    return collections


@st.cache_data(show_spinner="Retrieving data...", ttl=settings.cache_ttl)
def get_documents(collection_ids: List[str]) -> dict:
    documents = list()
    for collection_id in collection_ids:
        response = requests.get(url=f"{settings.api_url}/v1/documents/{collection_id}", headers={"Authorization": f"Bearer {settings.api_key}"})
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        for document in data:
            document["collection_id"] = collection_id
            documents.append(document)

    return documents


@st.cache_data(show_spinner=False, ttl=settings.cache_ttl)
def get_tokens():
    response = requests.get(
        url=f"{settings.api_url}/tokens/{st.session_state["user"]["id"]}", headers={"Authorization": f"Bearer {settings.api_key}"}
    )
    return response.json()["data"]
