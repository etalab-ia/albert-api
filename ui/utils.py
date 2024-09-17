import time
from typing import List

import requests
import streamlit as st
from streamlit_local_storage import LocalStorage

from config import BASE_URL, EMBEDDINGS_MODEL_TYPE, LANGUAGE_MODEL_TYPE, LOCAL_STORAGE_KEY

def set_config():
    st.set_page_config(
        page_title="Albert",
        page_icon="https://www.systeme-de-design.gouv.fr/uploads/apple_touch_icon_8ffa1fa80c.png",
        layout="wide",
        initial_sidebar_state="collapsed",
        menu_items={
            "Get Help": "mailto:etalab@modernisation.gouv.fr",
            "Report a bug": "https://github.com/etalab-ia/albert-api/issues",
            "About": "https://github.com/etalab-ia/albert-api",
        },
    )


def header():
    col1, col2 = st.columns([0.9, 0.1])
    with col1:
        st.subheader("Albert playground")

    # Authentication
    local_storage = LocalStorage()
    API_KEY = authenticate(local_storage=local_storage)
    with col2:
        logout = st.button("Logout")
        if logout:
            local_storage.deleteItem(LOCAL_STORAGE_KEY)
            st.rerun()
    st.markdown("***")
    
    return API_KEY

    
def check_api_key(base_url: str, api_key: str):
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(url=base_url.replace("/v1", "/health"), headers=headers)
    return response.status_code == 200


def authenticate(local_storage: LocalStorage):
    API_KEY = local_storage.getItem(LOCAL_STORAGE_KEY)
    if API_KEY is None:
        with st.form(key="my_form"):
            API_KEY = st.text_input(label="Please enter your API key", type="password")
            submit = st.form_submit_button(label="Submit")
            if submit:
                if check_api_key(base_url=BASE_URL, api_key=API_KEY):
                    local_storage.setItem(LOCAL_STORAGE_KEY, API_KEY)
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

    embeddings_models = [model["id"] for model in models if model["type"] == EMBEDDINGS_MODEL_TYPE]
    language_models = [model["id"] for model in models if model["type"] == LANGUAGE_MODEL_TYPE]

    return language_models, embeddings_models


def get_collections(api_key: str):
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{BASE_URL}/collections", headers=headers)
    assert response.status_code == 200
    collections = response.json()["data"]

    return collections


def get_files(api_key: str, collections: List[str]):
    files = {}
    headers = {"Authorization": f"Bearer {api_key}"}
    for collection in collections:
        response = requests.get(f"{BASE_URL}/files/{collection}", headers=headers)
        assert response.status_code == 200
        data = response.json()["data"]
        files[collection] = data

    return files


def upload_file(api_key: str, file, embeddings_model, collection_name):
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {"collection": collection_name, "embeddings_model": embeddings_model}
    files = {"files": (file.name, file.getvalue(), file.type)}
    response = requests.post(url=f"{BASE_URL}/files", params=params, files=files, headers=headers)
    data = response.json()["data"][0]
    status = data["status"]

    if status == "success":
        st.toast("Upload succeed", icon="✅")
    else:
        st.toast("Upload failed", icon="❌")
    return data


def delete_file(api_key: str, collection_name: str, file_id: str):
    url = f"{BASE_URL}/files/{collection_name}/{file_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.delete(url, headers=headers)
    if response.status_code == 204:
        st.toast("Delete succeed", icon="✅")
    else:
        st.toast("Delete failed", icon="❌")

    return False
