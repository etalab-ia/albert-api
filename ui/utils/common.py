from functools import lru_cache
import time
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
        API_KEY = st.session_state.get("API_KEY")
        if API_KEY is None:
            with st.form(key="my_form"):
                API_KEY = st.text_input(label="Please enter your API key", type="password")
                submit = st.form_submit_button(label="Submit")
                if submit:
                    if check_api_key(base_url=settings.base_url, api_key=API_KEY):
                        st.session_state["API_KEY"] = API_KEY
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
        API_KEY = authenticate()
        with col2:
            logout = st.button("Logout")
        if logout:
            st.session_state.pop("API_KEY")
            st.rerun()
        st.markdown("***")

    return API_KEY


def refresh_all_data(api_key: str) -> None:
    get_models.clear(api_key)
    get_collections.clear(api_key)
    get_documents.clear(api_key)


@st.cache_data(show_spinner=False, ttl=settings.cache_ttl)
def get_models(api_key: str, type: Literal[MODEL_TYPE_LANGUAGE, MODEL_TYPE_EMBEDDINGS, MODEL_TYPE_AUDIO, MODEL_TYPE_RERANK]) -> tuple[str, str, str]:
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{settings.base_url}/models", headers=headers)
    assert response.status_code == 200, f"{response.status_code} - {response.json()}"
    models = response.json()["data"]
    models = sorted([model["id"] for model in models if model["type"] == type and model["id"] not in settings.exclude_models])

    return models


@st.cache_data(show_spinner="Retrieving data...", ttl=settings.cache_ttl)
def get_collections(api_key: str) -> list:
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{settings.base_url}/collections", headers=headers)
    assert response.status_code == 200, f"{response.status_code} - {response.json()}"
    collections = response.json()["data"]

    collections = [
        collection
        for collection in collections
        if collection["model"] == settings.documents_embeddings_model or collection["id"] == COLLECTION_DISPLAY_ID_INTERNET
    ]

    return collections


@st.cache_data(show_spinner="Retrieving data...", ttl=settings.cache_ttl)
def get_documents(api_key: str, collection_ids: List[str]) -> dict:
    documents = list()
    headers = {"Authorization": f"Bearer {api_key}"}
    for collection_id in collection_ids:
        response = requests.get(f"{settings.base_url}/documents/{collection_id}", headers=headers)
        assert response.status_code == 200, f"{response.status_code} - {response.json()}"
        data = response.json()["data"]
        for document in data:
            document["collection_id"] = collection_id
            documents.append(document)

    return documents
