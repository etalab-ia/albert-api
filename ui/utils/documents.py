import datetime as dt

import pandas as pd
import requests
import streamlit as st

from config import BASE_URL, INTERNET_COLLECTION_DISPLAY_ID, PRIVATE_COLLECTION_TYPE
from utils.common import get_collections, get_documents, get_models


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


def upload_file(api_key: str, file, collection_id: str) -> None:
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"file": (file.name, file.getvalue(), file.type)}
    data = {"request": '{"collection": "%s"}' % collection_id}
    response = requests.post(f"{BASE_URL}/files", data=data, files=files, headers=headers)

    if response.status_code == 201:
        st.toast("Upload succeed", icon="✅")
    else:
        st.toast("Upload failed", icon="❌")


def delete_document(api_key: str, collection_id: str, document_id: str) -> None:
    url = f"{BASE_URL}/documents/{collection_id}/{document_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.delete(url, headers=headers)
    if response.status_code == 204:
        st.toast("Delete succeed", icon="✅")
    else:
        st.toast("Delete failed", icon="❌")


def load_data(api_key: str):
    try:
        _, embeddings_models, _, _ = get_models(api_key=api_key)
        collections = get_collections(api_key=api_key)
        collections = [collection for collection in collections if collection["id"] != INTERNET_COLLECTION_DISPLAY_ID]
        documents = get_documents(
            api_key=api_key,
            collection_ids=[collection["id"] for collection in collections if collection["type"] == PRIVATE_COLLECTION_TYPE],
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

    return embeddings_models, collections, documents, df_collections, df_files
