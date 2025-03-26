import pandas as pd
import streamlit as st

from ui.backend.common import get_collections, get_documents, get_models
from ui.backend.documents import create_collection, delete_collection, delete_document, upload_file
from ui.frontend.header import header
from ui.variables import COLLECTION_VISIBILITY_PRIVATE, MODEL_TYPE_EMBEDDINGS
from ui.settings import settings

header()
models = get_models(type=MODEL_TYPE_EMBEDDINGS)
if not settings.documents_model or settings.documents_model not in models:
    st.info("Please select a text-embeddings-inference model in the settings to activate the documents page.")
    st.stop()

with st.sidebar:
    if st.button(label="**:material/refresh: Refresh data**", key="refresh-data-documents", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


collections = get_collections()
documents = get_documents(
    collection_ids=[collection["id"] for collection in collections if collection["visibility"] == COLLECTION_VISIBILITY_PRIVATE],
)

# Collections
st.subheader(body="Collections")
st.dataframe(
    data=pd.DataFrame(
        data=[
            {
                "ID": collection["id"],
                "Name": collection["name"],
                "Visibility": collection["visibility"],
                "Documents": collection["documents"],
                "Updated at": pd.to_datetime(collection["updated_at"], unit="s"),
                "Created at": pd.to_datetime(collection["created_at"], unit="s"),
            }
            for collection in collections
        ],
    ),
    hide_index=True,
    use_container_width=True,
    column_config={
        "Updated at": st.column_config.DatetimeColumn(format="D MMM YYYY"),
        "Created at": st.column_config.DatetimeColumn(format="D MMM YYYY"),
    },
)

col1, col2 = st.columns(spec=2)
with col1:
    with st.expander(label="Create a collection", icon=":material/add_circle:"):
        collection_name = st.text_input(
            label="Collection name", placeholder="Mes documents", help="Create a private collection with the embeddings model of your choice."
        )
        if st.button(label="Create", disabled=not collection_name):
            create_collection(collection_name=collection_name, collection_model=settings.documents_model)

with col2:
    with st.expander(label="Delete a collection", icon=":material/delete_forever:"):
        collection = st.selectbox(
            label="Select collection to delete",
            options=[
                f"{collection["name"]} - {collection["id"]}"
                for collection in collections
                if collection["visibility"] == COLLECTION_VISIBILITY_PRIVATE
            ],
            key="delete_collection_selectbox",
        )
        collection_id = collection.split(" - ")[1] if collection else None
        if st.button(label="Delete", disabled=not collection_id, key="delete_collection_button"):
            delete_collection(api_key=st.session_state["user"].api_key, collection_id=collection_id)


if not collections:
    st.info(body="No collection found, create one to start.")
    st.stop()

# Documents
st.subheader(body="Documents")
st.dataframe(
    data=pd.DataFrame(
        data=[
            {
                "Collection": document["collection_id"],
                "ID": document["id"],
                "Name": document["name"],
                "Created at": pd.to_datetime(document["created_at"], unit="s"),
                "Chunks": document["chunks"],
            }
            for document in documents
        ]
    ),
    hide_index=True,
    use_container_width=True,
    column_config={
        "Created at": st.column_config.DatetimeColumn(format="D MMM YYYY"),
    },
)

col1, col2 = st.columns(spec=2)
with col1:
    with st.expander(label="Upload a file", icon=":material/upload_file:"):
        collection = st.selectbox(
            label="Select a collection",
            options=[
                f"{collection["name"]} - {collection["id"]}"
                for collection in collections
                if collection["visibility"] == COLLECTION_VISIBILITY_PRIVATE
            ],
            key="upload_file_selectbox",
        )
        collection_id = collection.split(" - ")[1] if collection else None
        file_to_upload = st.file_uploader(label="File", type=["pdf", "html", "json", "md"])
        submit_upload = st.button(label="Upload", disabled=not collection_id or not file_to_upload)
        if file_to_upload and submit_upload and collection_id:
            with st.spinner(text="Downloading and processing the document..."):
                result = upload_file(api_key=st.session_state["user"].api_key, file=file_to_upload, collection_id=collection_id)


with col2:
    with st.expander(label="Delete a document", icon=":material/delete_forever:"):
        document = st.selectbox(label="Select document to delete", options=[f"{document["name"]} - {document["id"]}" for document in documents])
        document_id = document.split(" - ")[1] if document else None
        document_collection = [document["collection_id"] for document in documents if document["id"] == document_id][0]
        if st.button(label="Delete", disabled=not document_id, key="delete_document_button"):
            delete_document(api_key=st.session_state["user"].api_key, collection_id=document_collection, document_id=document_id)
