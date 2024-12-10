import datetime as dt

import pandas as pd
import requests
import streamlit as st

from utils.common import get_collections, get_documents, settings
from utils.variables import COLLECTION_DISPLAY_ID_INTERNET, COLLECTION_TYPE_PRIVATE


def create_collection(api_key: str, collection_name: str, collection_model: str) -> None:
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.post(f"{settings.base_url}/collections", json={"name": collection_name, "model": collection_model}, headers=headers)
    if response.status_code == 201:
        st.toast("Create succeed", icon="✅")
        # clear cache
        get_collections.clear(api_key)
    else:
        st.toast("Create failed", icon="❌")


def delete_collection(api_key: str, collection_id: str) -> None:
    url = f"{settings.base_url}/collections/{collection_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.delete(url, headers=headers)
    if response.status_code == 204:
        st.toast("Delete succeed", icon="✅")
        # clear cache
        get_collections.clear(api_key)
    else:
        st.toast("Delete failed", icon="❌")


def upload_file(api_key: str, file, collection_id: str) -> None:
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"file": (file.name, file.getvalue(), file.type)}
    data = {"request": '{"collection": "%s"}' % collection_id}
    response = requests.post(f"{settings.base_url}/files", data=data, files=files, headers=headers)

    if response.status_code == 201:
        st.toast("Upload succeed", icon="✅")
        # clear cache
        get_collections.clear(api_key)  # since the number of documents in the collection has changed
        get_documents.clear(api_key)
    else:
        st.toast("Upload failed", icon="❌")


def delete_document(api_key: str, collection_id: str, document_id: str) -> None:
    url = f"{settings.base_url}/documents/{collection_id}/{document_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.delete(url, headers=headers)
    if response.status_code == 204:
        st.toast("Delete succeed", icon="✅")
        # clear cache
        get_collections.clear(api_key)  # since the number of documents in the collection has changed
        get_documents.clear(api_key)
    else:
        st.toast("Delete failed", icon="❌")


def load_data(api_key: str):
    try:
        collections = get_collections(api_key=api_key)
        collections = [collection for collection in collections if collection["id"] != COLLECTION_DISPLAY_ID_INTERNET]
        documents = get_documents(
            api_key=api_key,
            collection_ids=[collection["id"] for collection in collections if collection["type"] == COLLECTION_TYPE_PRIVATE],
        )
    except Exception as e:
        st.error("Error to fetch user data.")
        st.stop()

    # collections
    data = [
        {
            "ID": collection["id"],
            "Name": collection["name"],
            "Type": collection["type"],
            "Model": collection["model"],
            "Documents": collection["documents"],
        }
        for collection in collections
    ]
    columns = ["ID", "Name", "Type", "Model", "Documents"]
    df_collections = pd.DataFrame(data=data, columns=columns)

    # documents
    data = [
        {
            "Collection": document["collection_id"],
            "ID": document["id"],
            "Name": document["name"],
            "Created at": dt.datetime.fromtimestamp(document["created_at"]).strftime("%Y-%m-%d"),
            "Chunks": document["chunks"],
        }
        for document in documents
    ]
    columns = ["Collection", "ID", "Name", "Created at", "Chunks"]
    df_files = pd.DataFrame(data=data, columns=columns)

    return collections, documents, df_collections, df_files
