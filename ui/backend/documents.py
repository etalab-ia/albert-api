import time

import requests
import streamlit as st

from ui.backend.common import get_collections, get_documents
from ui.settings import settings


def create_collection(collection_name: str) -> None:
    headers = {"Authorization": f"Bearer {st.session_state["user"].api_key}"}
    response = requests.post(f"{settings.playground.api_url}/v1/collections", json={"name": collection_name}, headers=headers)

    if response.status_code != 201:
        st.toast(response.json()["detail"], icon="❌")
        return

    st.toast("Create succeed", icon="✅")
    get_collections.clear()
    time.sleep(0.5)
    st.rerun()


def delete_collection(collection_id: int) -> None:
    url = f"{settings.playground.api_url}/v1/collections/{collection_id}"
    headers = {"Authorization": f"Bearer {st.session_state["user"].api_key}"}
    response = requests.delete(url, headers=headers)

    if response.status_code != 204:
        st.toast(response.json()["detail"], icon="❌")
        return

    st.toast("Delete succeed", icon="✅")
    get_collections.clear()
    time.sleep(0.5)
    st.rerun()


def upload_file(file, collection_id: str) -> None:
    files = {"file": (file.name, file.getvalue(), file.type)}
    data = {"request": '{"collection": "%s"}' % collection_id}
    response = requests.post(
        url=f"{settings.playground.api_url}/v1/files",
        data=data,
        files=files,
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 201:
        st.toast(response.json()["detail"], icon="❌")
        return

    st.toast("Upload succeed", icon="✅")
    get_collections.clear()  # since the number of documents in the collection has changed
    get_documents.clear()
    time.sleep(0.5)
    st.rerun()


def delete_document(document_id: str) -> None:
    response = requests.delete(
        url=f"{settings.playground.api_url}/v1/documents/{document_id}",
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 204:
        st.toast(response.json()["detail"], icon="❌")
        return

    st.toast("Delete succeed", icon="✅")
    get_collections.clear()  # since the number of documents in the collection has changed
    get_documents.clear()
    time.sleep(0.5)
    st.rerun()
