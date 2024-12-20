import time

from openai import OpenAI
import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from config import BASE_URL, PRIVATE_COLLECTION_TYPE
from utils import get_collections, get_documents, get_models, header, set_config

# Config
set_config()
API_KEY = header()

openai_client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# Data
try:
    language_models, embeddings_models, _ = get_models(api_key=API_KEY)
    collections = get_collections(api_key=API_KEY)
    collections = [collection for collection in collections if collection["type"] == PRIVATE_COLLECTION_TYPE]
    documents = get_documents(api_key=API_KEY, collection_ids=[collection["id"] for collection in collections])
except Exception as e:
    st.error("Error to fetch user data.")
    st.stop()

# Sidebar
with st.sidebar:
    params = {"sampling_params": dict()}
    # @TODO

# Main
## Document
st.session_state.document_id = None if "document_id" not in st.session_state else st.session_state.document_id

st.subheader("1️⃣ Select a document")
st.info("Please select a document to generate a summary.")
document = st.selectbox("Document", options=[f"{document["id"]} - {document["name"]}" for document in documents])
document_id = document.split(" - ")[0]

with stylable_container(
    key="Summarize",
    css_styles="""
    button{
        float: right;
    }
    """,
):
    if st.button(label="Validate", key="validate_document"):
        st.session_state.document_id = document_id
        st.toast("Document validated !", icon="✅")
        time.sleep(2)
        st.rerun()

## TOC
st.session_state.toc = "" if "toc" not in st.session_state else st.session_state.toc
st.session_state.validate_toc = False if "validate_toc" not in st.session_state else st.session_state.validate_toc

st.markdown("***")
st.markdown(f"**state:**\n{st.session_state.toc}")
st.subheader("2️⃣ Create a table of content")

if not st.session_state.document_id:
    st.stop()

st.info(
    "For help the model to generate a summarize, you need to write a table of content of your document. Clic on *generate* button if you need an AI help."
)

toc = st.text_area(label="Table of content", value=st.session_state.toc, height=200)

with stylable_container(
    key="Summarize",
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
    col1, col2, col3 = st.columns([2, 6, 2])
    with col1:
        if st.button(label="✨ Generate", key="generate_toc", use_container_width=True):
            with st.spinner("✨ Generate..."):
                st.session_state.toc = "Generation"  # @TODO
                st.toast("Table of content generated !", icon="✅")
                time.sleep(2)
                st.rerun()
    with col3:
        if st.button("Validate", use_container_width=True):
            if toc:
                st.session_state.toc = toc
                st.session_state.validate_toc = True
                st.toast("Table of content validated !", icon="✅")
                time.sleep(2)
                st.rerun()
            else:
                st.toast("You have to write a table of content before validate it.", icon="❌")


## Summary
st.session_state.summary = "" if "summary" not in st.session_state else st.session_state.summary

st.markdown("***")
st.markdown(f"**state:**\n{st.session_state.summary}")
st.subheader("3️⃣ Generate a summary")

if not st.session_state.validate_toc:
    st.stop()

st.info("Here is the summary of your document.")

st.write("**Summary**")
st.code(st.session_state.summary, language="markdown", wrap_lines=True)

with stylable_container(
    key="Summarize",
    css_styles="""
    button{
        float: right;
    }
    """,
):
    if st.button("Generate", key="generate_summary"):
        with st.spinner("✨ Generate..."):
            st.session_state.summary = "Generation"  # @TODO
            st.toast("Summary generated !", icon="✅")
        time.sleep(2)
        st.rerun()

feedback = st.text_area(label="Feedback")

with stylable_container(
    key="Summarize",
    css_styles="""
    button{
        float: right;
    }
    """,
):
    if st.button("Give feedback", key="give_feedback"):
        if st.session_state.summary:
            with st.spinner("✨ Generate..."):
                st.session_state.summary = "Generation with feedback"  # @TODO
                st.toast("Summary generated with feedback !", icon="✅")
                time.sleep(2)
                st.rerun()
        else:
            st.toast("You have to generate a summary before give feedback.", icon="❌")
