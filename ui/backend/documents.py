import time
from typing import Optional

import requests
import streamlit as st

from ui.settings import settings


def create_collection(collection_name: str, collection_description: str) -> None:
    response = requests.post(
        url=f"{settings.playground.api_url}/v1/collections",
        json={"name": collection_name, "description": collection_description},
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 201:
        st.toast(response.json()["detail"], icon="❌")
        return

    st.toast("Create succeed", icon="✅")
    time.sleep(0.5)
    st.rerun()


def update_collection(collection_id: int, collection_name: Optional[str] = None, collection_description: Optional[str] = None) -> None:
    params = {}
    if collection_name:
        params["name"] = collection_name
    if collection_description:
        params["description"] = collection_description

    response = requests.patch(
        url=f"{settings.playground.api_url}/v1/collections/{collection_id}",
        json=params,
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 204:
        st.toast(response.json()["detail"], icon="❌")
        return

    st.toast("Update succeed", icon="✅")
    time.sleep(0.5)
    st.rerun()


def delete_collection(collection_id: int) -> None:
    response = requests.delete(
        url=f"{settings.playground.api_url}/v1/collections/{collection_id}",
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

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
