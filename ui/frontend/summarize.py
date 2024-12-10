import time

import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from ui.backend.common import get_collections, get_documents
from ui.backend.summarize import generate_summary, generate_toc, get_chunks, summary_with_feedback
from ui.frontend.header import header
from ui.variables import COLLECTION_TYPE_PRIVATE, MODEL_TYPE_LANGUAGE
from ui.frontend.utils import setup_selected_model
import logging

logger = logging.getLogger(__name__)
header()

# Data
try:
    collections = get_collections()
    collections = [collection for collection in collections if "type" in collection and collection["type"] == COLLECTION_TYPE_PRIVATE]
    documents = get_documents(collection_ids=[collection["id"] for collection in collections])
except Exception as e:
    logger.exception("Error while loading collections and documents")
    st.error(body=f"Error while loading collections and documents: {str(e)}")
    st.stop()

# Sidebar
with st.sidebar:
    new_chat = st.button(label="**:material/refresh: New summarize**", key="new", use_container_width=True)
    if new_chat:
        st.session_state.pop("collection_id", None)
        st.session_state.pop("document_id", None)
        st.session_state.pop("validate_toc", None)
        st.session_state.pop("toc", None)
        st.session_state.pop("summary", None)
        st.rerun()

    st.session_state["selected_model"] = setup_selected_model(model_type=MODEL_TYPE_LANGUAGE)

# Main
## Document
st.session_state.collection_id = None if "collection_id" not in st.session_state else st.session_state.collection_id
st.session_state.document_id = None if "document_id" not in st.session_state else st.session_state.document_id

st.subheader(body=":material/counter_1: Select a document")
st.info(body="Please select a document to generate a summary.")
document = st.selectbox(label="Document", options=[f"{document["id"]} - {document["name"]}" for document in documents])
if not document:
    st.warning(body="First upload a document via the Documents page.")
    st.stop()
document_id = int(document.split(" - ")[0])
collection_id = [document["collection_id"] for document in documents if document["id"] == document_id][0]

with stylable_container(
    key="Summarize",
    css_styles="""
    button{
        float: right;
    }
    """,
):
    if st.button(label="Validate", key="validate_document"):
        st.session_state.collection_id = collection_id
        st.session_state.document_id = document_id
        st.toast("Document validated !", icon="✅")
        time.sleep(2)
        st.rerun()

## TOC
st.session_state.toc = "" if "toc" not in st.session_state else st.session_state.toc
st.session_state.validate_toc = False if "validate_toc" not in st.session_state else st.session_state.validate_toc

st.markdown(body="***")
st.subheader(body=":material/counter_2: Create a table of content")

if not st.session_state.document_id:
    st.stop()
chunks = get_chunks(collection_id=collection_id, document_id=document_id)

st.info(
    body="For help the model to generate a summarize, you need to write a table of content of your document. Clic on *generate* button if you need an AI help."
)

toc = st.text_area(label="Table of content", value=st.session_state.toc, height=200)

with stylable_container(
    key="Toc",
    css_styles="""
    .left-button {
        float: left;
    }
    .right-button {
        float: right;
    .stButton {
        width: auto;
    }
    """,
):
    col1, col2, col3 = st.columns(spec=[2, 6, 2])
    with col1:
        if st.button(label="✨ Generate", key="generate_toc", use_container_width=True):
            with st.spinner(text="✨ Generate..."):
                st.session_state.toc = generate_toc(chunks=chunks, model=st.session_state["selected_model"])
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

with stylable_container(
    key="Summarize",
    css_styles="""
    button{
        float: right;
    }
    """,
):
    if st.button(label="✨ Generate", key="generate_summary"):
        st.session_state.summary = generate_summary(toc=st.session_state.toc, chunks=chunks, model=st.session_state["selected_model"])
        st.toast(body="Summary generated !", icon="✅")
        time.sleep(2)
        st.rerun()

feedback = st.text_area(label="Feedback")

with stylable_container(
    key="Feedback",
    css_styles="""
    button{
        float: right;
    }
    """,
):
    if st.button(label="Give feedback", key="give_feedback"):
        if st.session_state.summary:
            with st.spinner(text="✨ Generate..."):
                st.session_state.summary = summary_with_feedback(
                    feedback=feedback, summary=st.session_state.summary, model=st.session_state["selected_model"]
                )
                st.toast(body="Summary generated with feedback !", icon="✅")
                time.sleep(2)
                st.rerun()
        else:
            st.toast(body="You have to generate a summary before give feedback.", icon="❌")