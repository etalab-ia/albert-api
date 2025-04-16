import time

import requests
import streamlit as st

from ui.settings import settings


def create_collection(collection_name: str) -> None:
    headers = {"Authorization": f"Bearer {st.session_state["user"].api_key}"}
    response = requests.post(f"{settings.playground.api_url}/v1/collections", json={"name": collection_name}, headers=headers)

    if response.status_code != 201:
        st.toast(response.json()["detail"], icon="❌")
        return

    st.toast("Create succeed", icon="✅")
    time.sleep(0.5)
    st.rerun()


def delete_collection(collection_id: int) -> None:
    headers = {"Authorization": f"Bearer {st.session_state["user"].api_key}"}
    response = requests.delete(url=f"{settings.playground.api_url}/v1/collections/{collection_id}", headers=headers)

    if response.status_code != 204:
        st.toast(response.json()["detail"], icon="❌")
        return

    st.toast("Delete succeed", icon="✅")
    time.sleep(0.5)
    st.rerun()


def upload_file(file, collection_id: str) -> None:
    response = requests.post(
        url=f"{settings.playground.api_url}/v1/files",
        data={"request": '{"collection": "%s"}' % collection_id},
        files={"file": (file.name, file.getvalue(), file.type)},
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 201:
        st.toast(response.json()["detail"], icon="❌")
        return

    st.toast("Upload succeed", icon="✅")
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
    time.sleep(0.5)
    st.rerun()
