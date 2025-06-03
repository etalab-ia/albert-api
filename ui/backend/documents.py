import time
from typing import Optional

import requests
import streamlit as st

from ui.settings import settings


def create_collection(name: str, description: str) -> None:
    response = requests.post(
        url=f"{settings.playground.api_url}/v1/collections",
        json={"name": name, "description": description},
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 201:
        st.toast(response.json()["detail"], icon="❌")
        return

    st.toast("Create succeed", icon="✅")
    st.session_state["new_collection"] = False
    time.sleep(0.5)
    st.rerun()


def update_collection(collection_id: int, name: Optional[str] = None, description: Optional[str] = None) -> None:
    params = {}
    if name:
        params["name"] = name
    if description:
        params["description"] = description

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


def upload_document(file, collection_id: str) -> None:
    print('---------------upload----------------')
    response = requests.post(
        url=f"{settings.playground.api_url}/v1/documents",
        data={"collection": collection_id},
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
