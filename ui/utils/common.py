import time
from typing import List

import requests
import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from config import AUDIO_MODEL_TYPE, BASE_URL, EMBEDDINGS_MODEL_TYPE, INTERNET_COLLECTION_DISPLAY_ID, LANGUAGE_MODEL_TYPE, RERANK_MODEL_TYPE


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
                    if check_api_key(base_url=BASE_URL, api_key=API_KEY):
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


@st.cache_data(show_spinner=False)
def get_models(api_key: str) -> tuple[str, str, str]:
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{BASE_URL}/models", headers=headers)
    assert response.status_code == 200, f"{response.status_code} - {response.json()}"
    models = response.json()["data"]
    embeddings_models = sorted([model["id"] for model in models if model["type"] == EMBEDDINGS_MODEL_TYPE and model["status"] == "available"])
    language_models = sorted([model["id"] for model in models if model["type"] == LANGUAGE_MODEL_TYPE and model["status"] == "available"])
    audio_models = sorted([model["id"] for model in models if model["type"] == AUDIO_MODEL_TYPE and model["status"] == "available"])
    rerank_models = sorted([model["id"] for model in models if model["type"] == RERANK_MODEL_TYPE and model["status"] == "available"])
    return language_models, embeddings_models, audio_models, rerank_models


@st.cache_data(show_spinner="Retrieving data...")
def get_collections(api_key: str) -> list:
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{BASE_URL}/collections", headers=headers)
    assert response.status_code == 200, f"{response.status_code} - {response.json()}"
    collections = response.json()["data"]

    for collection in collections:
        if collection["id"] == INTERNET_COLLECTION_DISPLAY_ID:
            collection["name"] = "Internet"

    return collections


@st.cache_data(show_spinner="Retrieving data...")
def get_documents(api_key: str, collection_ids: List[str]) -> dict:
    documents = list()
    headers = {"Authorization": f"Bearer {api_key}"}
    for collection_id in collection_ids:
        response = requests.get(f"{BASE_URL}/documents/{collection_id}", headers=headers)
        assert response.status_code == 200, f"{response.status_code} - {response.json()}"
        data = response.json()["data"]
        for document in data:
            document["collection_id"] = collection_id
            documents.append(document)

    return documents
