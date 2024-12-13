import time
from typing import List

import requests
import streamlit as st

from config import BASE_URL, AUDIO_MODEL_TYPE, EMBEDDINGS_MODEL_TYPE, LANGUAGE_MODEL_TYPE


pc = st.get_option("theme.primaryColor")
bc = st.get_option("theme.backgroundColor")
sbc = st.get_option("theme.secondaryBackgroundColor")
tc = st.get_option("theme.textColor")


def header():
    gradient_text_html = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@100&display=swap');

    html, body, [class*="css"]  {
    font-family: 'Roboto', sans-serif;
    }
    .gradient-text {
        font-weight: normal;
        background: -webkit-linear-gradient(left, rgba(190, 190, 190, 0.8), rgba(235, 235, 235, 0.8));
        background: linear-gradient(to right, rgba(190, 190, 190, 0.8), rgba(235, 235, 235, 0.8));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: inline;
        font-size: 3em;
    }
    p {
        all: unset; /* Réinitialiser les styles par défaut, si nécessaire */
        display: block;
        font-size: 16px;
    }
    </style>
    <div class="gradient-text">Albert Playground</div>

    """
    return st.markdown(gradient_text_html, unsafe_allow_html=True)


def set_config():
    st.set_page_config(
        page_title="Albert",
        page_icon="https://www.systeme-de-design.gouv.fr/uploads/apple_touch_icon_8ffa1fa80c.png",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get Help": "mailto:etalab@modernisation.gouv.fr",
            "Report a bug": "https://github.com/etalab-ia/albert-api/issues",
            "About": "https://github.com/etalab-ia/albert-api",
        },
    )
    return header()


def check_api_key(base_url: str, api_key: str):
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
            else:
                st.stop()

    return API_KEY


@st.cache_data(show_spinner=False)
def get_models(api_key: str):
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{BASE_URL}/models", headers=headers)
    assert response.status_code == 200
    models = response.json()["data"]

    embeddings_models = [model["id"] for model in models if model["type"] == EMBEDDINGS_MODEL_TYPE and model["status"] == "available"]
    language_models = [model["id"] for model in models if model["type"] == LANGUAGE_MODEL_TYPE and model["status"] == "available"]
    audio_models = [model["id"] for model in models if model["type"] == AUDIO_MODEL_TYPE and model["status"] == "available"]
    return language_models, embeddings_models, audio_models


@st.cache_data(show_spinner="Getting the list of available collections...")
def get_collections(api_key: str):
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{BASE_URL}/collections", headers=headers)
    assert response.status_code == 200
    collections = response.json()["data"]

    return collections


def upload_file(api_key: str, file, collection_id: str) -> None:
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"file": (file.name, file.getvalue(), file.type)}
    data = {"request": '{"collection": "%s"}' % collection_id}
    response = requests.post(f"{BASE_URL}/files", data=data, files=files, headers=headers)

    if response.status_code == 201:
        st.toast("Upload succeed", icon="✅")
    else:
        st.toast("Upload failed", icon="❌")


@st.cache_data(show_spinner="Getting the list of available documents...")
def get_documents(api_key: str, collection_ids: List[str], count=0) -> dict:
    documents = list()
    headers = {"Authorization": f"Bearer {api_key}"}
    for collection_id in collection_ids:
        response = requests.get(f"{BASE_URL}/documents/{collection_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()["data"]
        for document in data:
            document["collection_id"] = collection_id
            documents.append(document)

    return documents


def delete_document(api_key: str, collection_id: str, document_id: str) -> None:
    url = f"{BASE_URL}/documents/{collection_id}/{document_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.delete(url, headers=headers)
    if response.status_code == 204:
        st.toast("Delete succeed", icon="✅")
    else:
        st.toast("Delete failed", icon="❌")


def create_collection(api_key: str, collection_name: str, collection_model: str) -> None:
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.post(f"{BASE_URL}/collections", json={"name": collection_name, "model": collection_model}, headers=headers)
    if response.status_code == 201:
        st.toast("Create succeed", icon="✅")
    else:
        st.toast("Create failed", icon="❌")


def delete_collection(api_key: str, collection_id: str) -> None:
    url = f"{BASE_URL}/collections/{collection_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.delete(url, headers=headers)
    if response.status_code == 204:
        st.toast("Delete succeed", icon="✅")
    else:
        st.toast("Delete failed", icon="❌")
