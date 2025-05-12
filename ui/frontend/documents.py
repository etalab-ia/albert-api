import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from ui.backend.documents import create_collection, delete_collection, delete_document, update_collection, upload_file
from ui.frontend.header import header
from ui.frontend.utils import ressources_selector

header()
if st.session_state["user"].id == 0:
    st.info("Master user can not create collections.")
    st.stop()


# Collections
with st.expander(label="Collections", expanded=not st.session_state.get("new_collection", False)):
    collections, selected_collection = ressources_selector(ressource="collection")

with st.sidebar:
    st.markdown(body="#### Collections")
    st.button(
        label="**:material/add: Create collection**",
        on_click=lambda: setattr(st.session_state, "new_collection", not st.session_state.get("new_collection", False)),
        use_container_width=True,
        type="primary" if st.session_state.get("new_collection", False) else "secondary",
    )

    if st.button(
        label="**:material/update: Update selected collection**",
        key="update_collection_button",
        use_container_width=True,
        disabled=st.session_state.get("new_collection", False) or not collections,
    ):
        update_collection(
            collection_id=selected_collection["id"],
            name=st.session_state.get("new_name"),
            description=st.session_state.get("new_description"),
        )

    if st.button(
        label="**:material/delete_forever: Delete selected collection**",
        key="delete_collection_button",
        use_container_width=True,
        disabled=st.session_state.get("new_collection", False) or not collections,
    ):
        delete_collection(collection_id=selected_collection["id"])

if not collections and not st.session_state.get("new_collection", False):
    st.warning(body="No collection found, create one to start.")
    st.stop()

collection_name = st.text_input(label="**Collection name**", placeholder="Enter collection name", value=selected_collection["name"])
collection_description = st.text_input(label="**Collection description**", placeholder="Enter collection description", value=selected_collection["description"])  # fmt: off

st.session_state["new_name"] = collection_name
st.session_state["new_description"] = collection_description

if st.session_state.get("new_collection", False):
    with stylable_container(key="Header", css_styles="button{float: right;}"):
        if st.button(label="**Create**", key="add_collection_button"):
            create_collection(
                name=st.session_state.get("new_name"),
                description=st.session_state.get("new_description"),
            )

# Documents
if not collections or st.session_state.get("new_collection", False):
    st.stop()

st.markdown(body=f"#### Documents of the *{"new" if st.session_state.get("new_collection", False) else selected_collection["name"]}* collection")
with st.expander(label="Documents", expanded=not st.session_state.get("new_document", False)):
    with st.spinner(text="Loading documents...", show_time=False):
        documents, selected_document = ressources_selector(ressource="document", filter=selected_collection["id"], per_page=10)
    with stylable_container(key="Header", css_styles="button{float: right;}"):
        if st.button(
            label="**:material/delete_forever: Delete selected document**",
            key="delete_document_button",
            disabled=st.session_state.get("new_document", False) or not documents,
        ):
            delete_document(document_id=selected_document["id"])

file_to_upload = st.file_uploader(label="File", type=["pdf", "html", "json", "md"])
with stylable_container(key="Header", css_styles="button{float: right;}"):
    if st.button(label="**:material/upload_file: Upload a new document**", disabled=not selected_collection["id"] or not file_to_upload):
        with st.spinner(text="Downloading and processing the document..."):
            upload_file(file=file_to_upload, collection_id=selected_collection["id"])
