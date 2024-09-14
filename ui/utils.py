from typing import List

import requests
import streamlit as st

from config import BASE_URL, DEFAULT_COLLECTION


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


def check_api_key(base_url: str, api_key: str):
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(url=base_url.replace("/v1", "/health"), headers=headers)
    return response.status_code == 200


@st.cache_data(show_spinner=False)
def get_models(api_key: str):
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{BASE_URL}/models", headers=headers)
    assert response.status_code == 200
    models = response.json()["data"]

    return models


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
