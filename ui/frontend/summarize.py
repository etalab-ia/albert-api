import time

import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from ui.backend.common import get_collections, get_documents, get_models
from ui.backend.summarize import generate_summary, generate_toc, get_chunks, summary_with_feedback
from ui.frontend.header import header
from ui.variables import MODEL_TYPE_LANGUAGE
import logging

logger = logging.getLogger(__name__)
header()
models = get_models(type=MODEL_TYPE_LANGUAGE)

# Sidebar
with st.sidebar:
    new_summarize = st.button(label="**:material/refresh: New summarize**", key="new", use_container_width=True)
    if new_summarize:
        st.session_state.pop("collection_id", None)
        st.session_state.pop("document_id", None)
        st.session_state.pop("document_name", None)
        st.session_state.pop("validate_toc", None)
        st.session_state.pop("toc", None)
        st.session_state.pop("summary", None)
        st.rerun()

    st.subheader(body="Summarize parameters")
    selected_model = st.selectbox(label="Language model", options=models)

# Main
# Collections
st.subheader(body=":material/counter_1: Select a document")

collections = get_collections(offset=st.session_state.get("collections_offset", 0), limit=10)
collection = st.selectbox(label="Select a collection", options=[f"{collection["name"]} ({collection["id"]})" for collection in collections])

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

if not collection:
    st.warning(body="First create a collection on the Documents page.")
    st.stop()

collection_id = int(collection.split("(")[-1].split(")")[0])

# Documents
documents = get_documents(collection_id=collection_id, offset=st.session_state.get("documents_offset", 0), limit=10)
document = st.selectbox(label="Select a document", options=[f"{document["name"]} ({document["id"]})" for document in documents])

## Pagination
_, left, center, right, _ = st.columns(spec=[10, 1.5, 1.5, 1.5, 10])
with left:
    if st.button(
        label="**:material/keyboard_double_arrow_left:**",
        key="pagination-documents-previous",
        disabled=st.session_state.get("documents_offset", 0) == 0,
        use_container_width=True,
    ):
        st.session_state.documents_offset = max(0, st.session_state.get("documents_offset", 0) - 10)
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
            st.session_state.documents_offset = st.session_state.get("documents_offset", 0) + 10
            st.rerun()


if document:
    document_name = "(".join(document.split("(")[:-1])
    document_id = int(document.split("(")[-1].split(")")[0])

if st.session_state.get("document_name"):
    st.info(body=f"Selected document: {st.session_state.get("document_name")} ({st.session_state.get("document_id")})")
else:
    st.info(body="Select document to summarize.")

with stylable_container(key="Summarize", css_styles="button{float: right;}"):
    if st.button(label="Validate", key="validate_document"):
        st.session_state.collection_id = collection_id
        st.session_state.document_id = document_id
        st.session_state.document_name = document_name
        st.toast("Document validated !", icon="✅")
        time.sleep(2)
        st.rerun()

## TOC
st.session_state.toc = "" if "toc" not in st.session_state else st.session_state.toc
st.session_state.validate_toc = False if "validate_toc" not in st.session_state else st.session_state.validate_toc

st.markdown(body="***")
st.subheader(body=":material/counter_2: Create a table of content")

if not st.session_state.get("document_id"):
    st.stop()
chunks = get_chunks(collection_id=collection_id, document_id=document_id)

st.info(
    body="For help the model to generate a summarize, you need to write a table of content of your document. Clic on *generate* button if you need an AI help."
)

toc = st.text_area(label="Table of content", value=st.session_state.toc, height=200)

with stylable_container(key="Toc", css_styles=".left-button{float: left;}.right-button{float: right;}.stButton{width: auto;}"):
    col1, col2, col3 = st.columns(spec=[2, 6, 2])
    with col1:
        if st.button(label="✨ Generate", key="generate_toc", use_container_width=True):
            with st.spinner(text="✨ Generate..."):
                st.session_state.toc = generate_toc(chunks=chunks, model=selected_model)
                st.toast(body="Table of content generated !", icon="✅")
                time.sleep(2)
                st.rerun()
    with col3:
        if st.button(label="Validate", use_container_width=True):
            if toc:
                st.session_state.toc = toc
                st.session_state.validate_toc = True
                st.toast(body="Table of content validated !", icon="✅")
                time.sleep(2)
                st.rerun()
            else:
                st.toast(body="You have to write a table of content before validate it.", icon="❌")


## Summary
st.session_state.summary = "" if "summary" not in st.session_state else st.session_state.summary

st.markdown(body="***")
st.subheader(body=":material/counter_3: Generate a summary")

if not st.session_state.validate_toc:
    st.stop()

st.info(body="Here is the summary of your document.")

st.write("**Summary**")
st.code(body=st.session_state.summary, language="markdown", wrap_lines=True)

with stylable_container(key="Summarize", css_styles="button{float: right;}"):
    if st.button(label="✨ Generate", key="generate_summary"):
        st.session_state.summary = generate_summary(toc=st.session_state.toc, chunks=chunks, model=selected_model)
        st.toast(body="Summary generated !", icon="✅")
        time.sleep(2)
        st.rerun()

feedback = st.text_area(label="Feedback")

with stylable_container(key="Feedback", css_styles="button{float: right;}"):
    if st.button(label="Give feedback", key="give_feedback"):
        if st.session_state.summary:
            with st.spinner(text="✨ Generate..."):
                st.session_state.summary = summary_with_feedback(feedback=feedback, summary=st.session_state.summary, model=selected_model)
                st.toast(body="Summary generated with feedback !", icon="✅")
                time.sleep(2)
                st.rerun()
        else:
            st.toast(body="You have to generate a summary before give feedback.", icon="❌")
