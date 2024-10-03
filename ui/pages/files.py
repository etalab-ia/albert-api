import datetime as dt
import time

import pandas as pd
import streamlit as st

from utils import create_collection, delete_file, get_collections, get_files, get_models, header, set_config, upload_file, delete_collection
from config import INTERNET_COLLECTION_ID, PRIVATE_COLLECTION_TYPE

# Config
set_config()
API_KEY = header()

# Data
try:
    language_models, embeddings_models = get_models(api_key=API_KEY)
    collections = get_collections(api_key=API_KEY)
    collections = [collection for collection in collections if collection["id"] != INTERNET_COLLECTION_ID]
    file_data = get_files(
        api_key=API_KEY, collection_ids=[collection["id"] for collection in collections if collection["type"] == PRIVATE_COLLECTION_TYPE]
    )
except Exception as e:
    st.error("Error to fetch user data.")
    st.stop()

## Collections
data = [{"ID": collection["id"], "Name": collection["name"], "Type": collection["type"], "Model": collection["model"]} for collection in collections]
df_collections = pd.DataFrame(data, columns=["ID", "Name", "Type", "Model"])

st.subheader("Collections")
st.dataframe(df_collections, hide_index=True, use_container_width=True)

col1, col2 = st.columns(2)
with col1:
    with st.expander("Create a collection", icon="🗂️"):
        collection_name = st.text_input(
            "Collection name", placeholder="Mes documents", help="Create a private collection with the embeddings model of your choice."
        )
        collection_model = st.selectbox("Embeddings model", embeddings_models)
        submit_create = st.button("Create", disabled=not collection_name or not collection_model)
        if submit_create:
            create_collection(api_key=API_KEY, collection_name=collection_name, collection_model=collection_model)
            time.sleep(0.5)
            st.rerun()

with col2:
    with st.expander("Delete a collection", icon="📦"):
        collection = st.selectbox(
            "Select collection to delete",
            [f"{collection["name"]} - {collection["id"]}" for collection in collections],
            key="delete_collection_selectbox",
        )
        collection_id = collection.split(" - ")[-1] if collection else None
        submit_delete = st.button("Delete", disabled=not collection_id, key="delete_collection_button")
        if submit_delete:
            delete_collection(api_key=API_KEY, collection_id=collection_id)
            time.sleep(0.5)
            st.rerun()

if not collections:
    st.info("No collection found, create one to start.")
    st.stop()

# Files
table = []
for collection_id, files in file_data.items():
    for file in files:
        table.append(
            [
                collection_id,
                file["id"],
                file["name"],
                f"{file["bytes"] / (1024 * 1024):.2f} MB",
                dt.datetime.fromtimestamp(file["created_at"]).strftime("%Y-%m-%d"),
            ]
        )

columns = ["Collection", "ID", "Name", "Size", "Created at"]
df_files = pd.DataFrame(table, columns=columns)

st.subheader("Files")
st.dataframe(df_files, hide_index=True, use_container_width=True)

col1, col2 = st.columns(2)
with col1:
    with st.expander("Upload a file", icon="📑"):
        collection = st.selectbox(
            "Select collection to delete", [f"{collection["name"]} - {collection["id"]}" for collection in collections], key="upload_file_selectbox"
        )
        collection_id = collection.split(" - ")[-1]
        file_to_upload = st.file_uploader("File", type=["pdf", "html", "json"])
        submit_upload = st.button("Upload", disabled=not collection_id or not file_to_upload)
        if file_to_upload and submit_upload and collection_id:
            with st.spinner("Téléchargement et traitement du document en cours..."):
                result = upload_file(api_key=API_KEY, file=file_to_upload, collection_id=collection_id)
                time.sleep(0.5)
                st.rerun()

## Delete files
with col2:
    with st.expander("Delete a file", icon="🗑️"):
        file_id = st.selectbox("Select file to delete", df_files["ID"])
        if file_id:
            file_collection = [collection_id for collection_id, file in file_data.items() if file_id in [f["id"] for f in file]][0]
        submit_delete = st.button("Delete", disabled=not file_id, key="delete_file_button")
        if submit_delete:
            delete_file(api_key=API_KEY, collection_id=file_collection, file_id=file_id)
            time.sleep(0.5)
            st.rerun()
