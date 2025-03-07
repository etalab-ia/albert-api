import time

import requests
import streamlit as st

from utils.common import get_collections, get_documents, settings


def create_collection(api_key: str, collection_name: str, collection_model: str) -> None:
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.post(f"{settings.api_url}/v1/collections", json={"name": collection_name, "model": collection_model}, headers=headers)
    if response.status_code == 201:
        st.toast("Create succeed", icon="✅")
        get_collections.clear(api_key)
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast("Create failed", icon="❌")


def delete_collection(api_key: str, collection_id: str) -> None:
    url = f"{settings.api_url}/v1/collections/{collection_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.delete(url, headers=headers)
    if response.status_code == 204:
        st.toast("Delete succeed", icon="✅")
        get_collections.clear(api_key)
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast("Delete failed", icon="❌")


def upload_file(api_key: str, file, collection_id: str) -> None:
    files = {"file": (file.name, file.getvalue(), file.type)}
    data = {"request": '{"collection": "%s"}' % collection_id}
    response = requests.post(url=f"{settings.api_url}/v1/files", data=data, files=files, headers={"Authorization": f"Bearer {api_key}"})

    if response.status_code == 201:
        st.toast("Upload succeed", icon="✅")
        get_collections.clear()  # since the number of documents in the collection has changed
        get_documents.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast("Upload failed", icon="❌")


def delete_document(api_key: str, collection_id: str, document_id: str) -> None:
    response = requests.delete(url=f"{settings.api_url}/v1/documents/{collection_id}/{document_id}", headers={"Authorization": f"Bearer {api_key}"})
    if response.status_code == 204:
        st.toast("Delete succeed", icon="✅")
        get_collections.clear()  # since the number of documents in the collection has changed
        get_documents.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast("Delete failed", icon="❌")
