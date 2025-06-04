import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from ui.backend.documents import create_collection, delete_collection, delete_document, update_collection, upload_document
from ui.frontend.header import header
from ui.frontend.utils import input_new_collection_description, input_new_collection_name, ressources_selector

header()
if st.session_state["user"].id == 0:
    st.info("Master user can not create collections.")
    st.stop()


# Collections
with st.expander(label="Collections", expanded=not st.session_state.get("new_collection", False)):
    collections, selected_collection = ressources_selector(ressource="collection")
    st.session_state["no_collections"] = True if collections == [] else False
    with stylable_container(key="Header", css_styles="button{float: right;}"):
        if st.button(
            label="**:material/delete_forever: Delete**",
            key="delete_collection_button",
            disabled=st.session_state.get("new_collection", False) or st.session_state["no_collections"],
        ):
            delete_collection(collection_id=selected_collection["id"])


collection_name = input_new_collection_name(selected_collection=selected_collection)
collection_description = input_new_collection_description(selected_collection=selected_collection)

if st.session_state.get("new_collection", False):
    with stylable_container(key="Header", css_styles="button{float: right;}"):
        if st.button(label="**Create**", key="add_collection_button"):
            create_collection(name=collection_name, description=collection_description)
if st.session_state.get("update_collection", False):
    with stylable_container(key="Header", css_styles="button{float: right;}"):
        if st.button(label="**Update**", key="validate_update_collection_button"):
            update_collection(collection_id=selected_collection["id"], name=collection_name, description=collection_description)


with st.sidebar:
    st.markdown(body="#### Collections")
    col1, col2 = st.columns(spec=2)
    with col1:
        st.button(
            label="**:material/add: Create**",
            key="create_collection_button",
            on_click=lambda: setattr(st.session_state, "new_collection", not st.session_state.get("new_collection", False)),
            use_container_width=True,
            type="primary" if st.session_state.get("new_collection", False) else "secondary",
            disabled=st.session_state.get("update_collection", False),
        )
    with col2:
        st.button(
            label="**:material/update: Update**",
            key="update_collection_button",
            on_click=lambda: setattr(st.session_state, "update_collection", not st.session_state.get("update_collection", False)),
            use_container_width=True,
            disabled=st.session_state.get("new_collection", False) or st.session_state["no_collections"],
            type="primary" if st.session_state.get("update_collection", False) else "secondary",
        )

# Documents
if not collections or st.session_state.get("new_collection", False) or st.session_state.get("update_collection", False):
    st.stop()

st.markdown(body=f"#### Documents of the *{"new" if st.session_state.get("new_collection", False) else selected_collection["name"]}* collection")
with st.expander(label="Documents", expanded=not st.session_state.get("new_document", False)):
    with st.spinner(text="Loading documents...", show_time=False):
        documents, selected_document = ressources_selector(ressource="document", filter=selected_collection["id"], per_page=10)
    with stylable_container(key="Header", css_styles="button{float: right;}"):
        if st.button(
            label="**:material/delete_forever: Delete**",
            key="delete_document_button",
            disabled=st.session_state.get("new_document", False) or not documents,
        ):
            delete_document(document_id=selected_document["id"])

file_to_upload = st.file_uploader(label="File", type=["pdf", "html", "json", "md"])
with stylable_container(key="Header", css_styles="button{float: right;}"):
    if st.button(label="**:material/upload_file: Upload a new document**", disabled=not selected_collection["id"] or not file_to_upload):
        with st.spinner(text="Downloading and processing the document..."):
            upload_document(file=file_to_upload, collection_id=selected_collection["id"])
