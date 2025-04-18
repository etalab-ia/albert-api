import pandas as pd
import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from ui.backend.common import get_collections, get_documents
from ui.backend.documents import create_collection, update_collection, delete_collection, delete_document, upload_file
from ui.frontend.header import header
from ui.settings import settings
from ui.variables import COLLECTION_VISIBILITY_PRIVATE

header()
with st.sidebar:
    if st.button(label="**:material/refresh: Refresh data**", key="refresh-data-documents", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# Collections
st.subheader(body="Collections")

collections = get_collections(offset=st.session_state.get("collections_offset", 0), limit=10)
private_collections = [collection for collection in collections if collection["visibility"] == COLLECTION_VISIBILITY_PRIVATE]

st.dataframe(
    data=pd.DataFrame(
        data=[
            {
                "ID": collection["id"],
                "Name": collection["name"],
                "Visibility": collection["visibility"],
                "Owner": collection["owner"],
                "Documents": collection["documents"],
                "Description": collection["description"],
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

## Pagination
_, left, center, right, _ = st.columns(spec=[10, 1.5, 1.5, 1.5, 10])
with left:
    if st.button(
        label="**:material/keyboard_double_arrow_left:**",
        key="pagination-collections-previous",
        disabled=st.session_state.get("collections_offset", 0) == 0,
        use_container_width=True,
    ):
        st.session_state["collections_offset"] = max(0, st.session_state.get("collections_offset", 0) - 10)
        st.rerun()

with center:
    st.button(label=str(round(st.session_state.get("collections_offset", 0) / 10)), key="pagination-collections-offset", use_container_width=True)

with right:
    with stylable_container(key="pagination-collections-next", css_styles="button{float: right;}"):
        if st.button(
            label="**:material/keyboard_double_arrow_right:**",
            key="pagination-collections-next",
            disabled=len(collections) < 10,
            use_container_width=True,
        ):
            st.session_state["collections_offset"] = st.session_state.get("collections_offset", 0) + 10
            st.rerun()


col1, col2, col3 = st.columns(spec=3)
with col1:
    with st.expander(label="Create a collection", icon=":material/add_circle:"):
        collection_name = st.text_input(label="Collection name", placeholder="Enter collection name")
        collection_description = st.text_input(label="Collection description (optional)", placeholder="Enter collection description")

        if st.button(label="Create", disabled=not collection_name or st.session_state["user"].name == settings.auth.master_username):
            create_collection(collection_name=collection_name, collection_description=collection_description)
with col2:
    with st.expander(label="Update a collection", icon=":material/update:"):
        collection_name = st.selectbox(
            label="Select collection to update",
            options=[f"{collection["name"]} ({collection["id"]})" for collection in private_collections],
        )
        selected_collection = [collection for collection in private_collections if f"{collection["name"]} ({collection["id"]})" == collection_name]

        collection_name = selected_collection[0]["name"] if selected_collection else None
        collection_description = selected_collection[0]["description"] if selected_collection else None
        collection_id = selected_collection[0]["id"] if selected_collection else None

        new_collection_name = st.text_input(label="Collection name", placeholder=collection_name)
        new_collection_description = st.text_input(label="Collection description", placeholder=collection_description)

        if st.button(label="Update", disabled=not collection_id):
            update_collection(collection_id=collection_id, collection_name=new_collection_name, collection_description=new_collection_description)

with col3:
    with st.expander(label="Delete a collection", icon=":material/delete_forever:"):
        collection_name = st.selectbox(
            label="Select collection to delete",
            options=[f"{collection["name"]} ({collection["id"]})" for collection in private_collections],
            key="delete_collection_selectbox",
        )
        collection_id = [collection["id"] for collection in private_collections if f"{collection["name"]} ({collection["id"]})" == collection_name]
        collection_id = collection_id[0] if collection_id else None
        if st.button(
            label="Delete",
            disabled=not collection_id or st.session_state["user"].name == settings.auth.master_username,
            key="delete_collection_button",
        ):
            delete_collection(collection_id=collection_id)

if not collections:
    st.info(body="No collection found, create one to start.")
    st.stop()

st.divider()

# Documents
st.subheader(body="Documents")

collection_name = st.selectbox(
    label="Select a collection",
    options=[f"{collection["name"]} ({collection["id"]})" for collection in private_collections],
    key="select_collection_selectbox",
)
collection_id = [collection["id"] for collection in private_collections if f"{collection["name"]} ({collection["id"]})" == collection_name]
collection_id = collection_id[0] if collection_id else None

documents = get_documents(collection_id=collection_id, offset=st.session_state.get("documents_offset", 0), limit=10)

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

## Pagination
_, left, center, right, _ = st.columns(spec=[10, 1.5, 1.5, 1.5, 10])

with left:
    if st.button(
        label="**:material/keyboard_double_arrow_left:**",
        key="pagination-documents-previous",
        disabled=st.session_state.get("documents_offset", 0) == 0,
        use_container_width=True,
    ):
        st.session_state["documents_offset"] = max(0, st.session_state.get("documents_offset", 0) - 10)
        st.rerun()

with center:
    st.button(label=str(round(st.session_state.get("documents_offset", 0) / 10)), key="pagination-documents-offset", use_container_width=True)

with right:
    with stylable_container(key="pagination-documents-next", css_styles="button{float: right;}"):
        if st.button(
            label="**:material/keyboard_double_arrow_right:**",
            key="pagination-documents-next",
            disabled=len(documents) < 10,
            use_container_width=True,
        ):
            st.session_state["documents_offset"] = st.session_state.get("documents_offset", 0) + 10
            st.rerun()

col1, col2 = st.columns(spec=2)
with col1:
    with st.expander(label="Upload a file", icon=":material/upload_file:"):
        file_to_upload = st.file_uploader(label="File", type=["pdf", "html", "json", "md"])
        if st.button(label="Upload", disabled=not collection_id or not file_to_upload):
            with st.spinner(text="Downloading and processing the document..."):
                upload_file(file=file_to_upload, collection_id=collection_id)

with col2:
    with st.expander(label="Delete a document", icon=":material/delete_forever:"):
        document_name = st.selectbox(label="Select document to delete", options=[f"{document["name"]} ({document["id"]})" for document in documents])
        document_id = [document["id"] for document in documents if f"{document["name"]} ({document["id"]})" == document_name]
        document_id = document_id[0] if document_id else None

        if st.button(label="Delete", disabled=not document_id, key="delete_document_button"):
            delete_document(document_id=document_id)
