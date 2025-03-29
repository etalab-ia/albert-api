import pandas as pd
import streamlit as st

from ui.backend.common import get_collections, get_documents
from ui.backend.documents import create_collection, delete_collection, delete_document, upload_file
from ui.frontend.header import header
from ui.variables import COLLECTION_VISIBILITY_PRIVATE
from ui.settings import settings

header()
with st.sidebar:
    if st.button(label="**:material/refresh: Refresh data**", key="refresh-data-documents", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


collections = get_collections()
private_collections = [collection for collection in collections if collection["visibility"] == COLLECTION_VISIBILITY_PRIVATE]
documents = get_documents(collection_ids=[collection["id"] for collection in private_collections])

# Collections
st.subheader(body="Collections")
st.dataframe(
    data=pd.DataFrame(
        data=[
            {
                "ID": collection["id"],
                "Name": collection["name"],
                "Visibility": collection["visibility"],
                "Owner": collection["owner"],
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
            label="Collection name", placeholder="Enter collection name", help="Create a private collection with the embeddings model of your choice."
        )
        if st.button(label="Create", disabled=not collection_name or st.session_state["user"].name == settings.master_username):
            create_collection(collection_name=collection_name)

with col2:
    with st.expander(label="Delete a collection", icon=":material/delete_forever:"):
        collection_name = st.selectbox(
            label="Select collection to delete", options=[collection["name"] for collection in private_collections], key="delete_collection_selectbox"
        )
        collection_id = [collection["id"] for collection in private_collections if collection["name"] == collection_name]
        collection_id = collection_id[0] if collection_id else None
        if st.button(
            label="Delete",
            disabled=not collection_id or st.session_state["user"].name == settings.master_username,
            key="delete_collection_button",
        ):
            delete_collection(collection_id=collection_id)


if not collections:
    st.info(body="No collection found, create one to start.")
    st.stop()

# Documents
st.subheader(body="Documents")
st.dataframe(
    data=pd.DataFrame(
        data=[
            {
                "ID": document["id"],
                "Collection": [collection["name"] for collection in collections if collection["id"] == document["collection_id"]][0],
                "Name": document["name"],
                "Chunks": document["chunks"],
                "Created at": pd.to_datetime(document["created_at"], unit="s"),
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
        collection_name = st.selectbox(
            label="Select a collection", options=[collection["name"] for collection in private_collections], key="upload_file_selectbox"
        )
        collection_id = [collection["id"] for collection in private_collections if collection["name"] == collection_name]
        collection_id = collection_id[0] if collection_id else None
        file_to_upload = st.file_uploader(label="File", type=["pdf", "html", "json", "md"])
        submit_upload = st.button(label="Upload", disabled=not collection_id or not file_to_upload)
        if file_to_upload and submit_upload and collection_id:
            with st.spinner(text="Downloading and processing the document..."):
                result = upload_file(file=file_to_upload, collection_id=collection_id)


with col2:
    with st.expander(label="Delete a document", icon=":material/delete_forever:"):
        document_name = st.selectbox(label="Select document to delete", options=[f"{document["name"]} ({document["id"]})" for document in documents])
        document_id = [document["id"] for document in documents if f"{document["name"]} ({document["id"]})" == document_name]
        document_id = document_id[0] if document_id else None
        document_collection = [document["collection_id"] for document in documents if document["id"] == document_id]
        document_collection = document_collection[0] if document_id else None

        if st.button(label="Delete", disabled=not document_id, key="delete_document_button"):
            delete_document(collection_id=document_collection, document_id=document_id)
