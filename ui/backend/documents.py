import time
from typing import Optional

import requests
import streamlit as st

from ui.settings import settings


def create_collection(name: str, description: str) -> None:
    """Version originale pour compatibilité"""
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


def create_collection_with_id(name: str, description: str) -> Optional[int]:
    """
    Crée une collection et retourne son ID.
    """
    response = requests.post(
        url=f"{settings.playground.api_url}/v1/collections",
        json={"name": name, "description": description},
        headers={"Authorization": f"Bearer {st.session_state['user'].api_key}"},
    )

    if response.status_code != 201:
        st.toast(response.json()["detail"], icon="❌")
        return None

    # Récupérer l'ID de la collection créée
    collection_data = response.json()
    collection_id = collection_data.get("id")
    
    st.toast("Collection créée avec succès", icon="✅")
    return collection_id


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


def upload_document(file, collection_id: str) -> bool:
    """
    Upload un document vers une collection.
    Retourne True si succès, False sinon.
    """
    try:
        response = requests.post(
            url=f"{settings.playground.api_url}/v1/documents",
            data={"collection": collection_id},
            files={"file": (file.name, file.getvalue(), file.type)},
            headers={"Authorization": f"Bearer {st.session_state['user'].api_key}"},
        )

        if response.status_code != 201:
            st.toast(response.json()["detail"], icon="❌")
            return False

        st.toast("Upload succeed", icon="✅")
        return True
        
    except Exception as e:
        st.toast(f"Erreur upload: {str(e)}", icon="❌")
        return False


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