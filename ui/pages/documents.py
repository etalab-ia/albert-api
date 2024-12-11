import datetime as dt
import time

import pandas as pd
import streamlit as st

from config import INTERNET_COLLECTION_DISPLAY_ID, PRIVATE_COLLECTION_TYPE
from utils import (
    create_collection,
    delete_collection,
    delete_document,
    get_collections,
    get_documents,
    get_models,
    header,
    set_config,
    upload_file,
    authenticate,
)

# Config
set_config()
header()
API_KEY = authenticate()
st.session_state["count"] = 0


# Data
def load_stuff():
    try:
        language_models, embeddings_models, _ = get_models(api_key=API_KEY)
        collections = get_collections(api_key=API_KEY)
        collections = [collection for collection in collections if collection["id"] != INTERNET_COLLECTION_DISPLAY_ID]
        documents = get_documents(
            api_key=API_KEY,
            collection_ids=[collection["id"] for collection in collections if collection["type"] == PRIVATE_COLLECTION_TYPE],
            count=st.session_state["count"],
        )
    except Exception as e:
        st.error("Error to fetch user data.")
        st.stop()

    ## Collections
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
    df_collections = pd.DataFrame(data, columns=columns)
    return language_models, embeddings_models, collections, documents, df_collections


st.subheader("Collections")
if st.button("⟳ Refresh collections and documents lists"):
    st.cache_data.clear()
    language_models, embeddings_models, collections, documents, df_collections = load_stuff()

language_models, embeddings_models, collections, documents, df_collections = load_stuff()
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
            [f"{collection["id"]} - {collection["name"]}" for collection in collections if collection["type"] == PRIVATE_COLLECTION_TYPE],
            key="delete_collection_selectbox",
        )
        collection_id = collection.split(" - ")[0] if collection else None
        submit_delete = st.button("Delete", disabled=not collection_id, key="delete_collection_button")
        if submit_delete:
            delete_collection(api_key=API_KEY, collection_id=collection_id)
            time.sleep(0.5)
            st.rerun()

if not collections:
    st.info("No collection found, create one to start.")
    st.stop()

# Documents
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
df_files = pd.DataFrame(data, columns=columns)

st.subheader("Documents")
st.dataframe(df_files, hide_index=True, use_container_width=True)

col1, col2 = st.columns(2)
with col1:
    with st.expander("Upload a file", icon="📑"):
        collection = st.selectbox(
            "Select a collection",
            [f"{collection["id"]} - {collection["name"]}" for collection in collections if collection["type"] == PRIVATE_COLLECTION_TYPE],
            key="upload_file_selectbox",
        )
        collection_id = collection.split(" - ")[0] if collection else None
        file_to_upload = st.file_uploader("File", type=["pdf", "html", "json", "md"])
        submit_upload = st.button("Upload", disabled=not collection_id or not file_to_upload)
        if file_to_upload and submit_upload and collection_id:
            with st.spinner("Téléchargement et traitement du document en cours..."):
                result = upload_file(api_key=API_KEY, file=file_to_upload, collection_id=collection_id)
                time.sleep(0.5)
                st.rerun()

## Delete files
with col2:
    with st.expander("Delete a document", icon="🗑️"):
        document = st.selectbox("Select document to delete", [f"{document["id"]} - {document["name"]}" for document in documents])
        document_id = document.split(" - ")[0] if document else None
        submit_delete = st.button("Delete", disabled=not document_id, key="delete_document_button")
        if submit_delete:
            document_collection = [document["collection_id"] for document in documents if document["id"] == document_id][0]
            delete_document(api_key=API_KEY, collection_id=document_collection, document_id=document_id)
            time.sleep(0.5)
            st.rerun()
