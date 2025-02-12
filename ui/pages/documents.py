import time

import streamlit as st

from config import COLLECTION_TYPE__PRIVATE
from utils import create_collection, delete_collection, delete_document, header, load_data, refresh_all_data, upload_file

API_KEY = header()

with st.sidebar:
    if st.button(label="**:material/refresh: Rafraîchir les données**", key="refresh", use_container_width=True):
        refresh_all_data(api_key=API_KEY)

# Data
embeddings_models, collections, documents, df_collections, df_files = load_data(api_key=API_KEY)

# Collections
st.subheader(body="Collections")
st.dataframe(data=df_collections, hide_index=True, use_container_width=True)

col1, col2 = st.columns(spec=2)
with col1:
    with st.expander(label="Create a collection", icon=":material/add_circle:"):
        collection_name = st.text_input(
            label="Collection name", placeholder="Mes documents", help="Create a private collection with the embeddings model of your choice."
        )
        collection_model = st.selectbox(label="Embeddings model", options=embeddings_models)
        submit_create = st.button(label="Create", disabled=not collection_name or not collection_model)
        if submit_create:
            create_collection(api_key=API_KEY, collection_name=collection_name, collection_model=collection_model)
            time.sleep(0.5)
            st.rerun()

with col2:
    with st.expander(label="Delete a collection", icon=":material/delete_forever:"):
        collection = st.selectbox(
            label="Select collection to delete",
            options=[f"{collection['name']} - {collection['id']}" for collection in collections if collection["type"] == COLLECTION_TYPE__PRIVATE],
            key="delete_collection_selectbox",
        )
        collection_id = collection.split(" - ")[1] if collection else None
        submit_delete = st.button(label="Delete", disabled=not collection_id, key="delete_collection_button")
        if submit_delete:
            delete_collection(api_key=API_KEY, collection_id=collection_id)
            time.sleep(0.5)
            st.rerun()

if not collections:
    st.info(body="No collection found, create one to start.")
    st.stop()

# Documents
st.subheader(body="Documents")
st.dataframe(data=df_files, hide_index=True, use_container_width=True)

col1, col2 = st.columns(spec=2)
with col1:
    with st.expander(label="Upload a file", icon=":material/upload_file:"):
        collection = st.selectbox(
            label="Select a collection",
            options=[f"{collection['name']} - {collection['id']}" for collection in collections if collection["type"] == COLLECTION_TYPE__PRIVATE],
            key="upload_file_selectbox",
        )
        collection_id = collection.split(" - ")[1] if collection else None
        file_to_upload = st.file_uploader(label="File", type=["pdf", "html", "json", "md"])
        submit_upload = st.button(label="Upload", disabled=not collection_id or not file_to_upload)
        if file_to_upload and submit_upload and collection_id:
            with st.spinner(text="Downloading and processing the document..."):
                result = upload_file(api_key=API_KEY, file=file_to_upload, collection_id=collection_id)
                time.sleep(0.5)
                st.rerun()

## Delete files
with col2:
    with st.expander(label="Delete a document", icon=":material/delete_forever:"):
        document = st.selectbox(label="Select document to delete", options=[f"{document['name']} - {document['id']}" for document in documents])
        document_id = document.split(" - ")[1] if document else None
        submit_delete = st.button(label="Delete", disabled=not document_id, key="delete_document_button")
        if submit_delete:
            document_collection = [document["collection_id"] for document in documents if document["id"] == document_id][0]
            delete_document(api_key=API_KEY, collection_id=document_collection, document_id=document_id)
            time.sleep(0.5)
            st.rerun()
