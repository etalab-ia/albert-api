import time

import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from ui.backend.common import get_limits, get_models
from ui.backend.summarize import generate_summary, generate_toc, get_chunks, summary_with_feedback
from ui.frontend.header import header
from ui.frontend.utils import resources_selector
from ui.variables import MODEL_TYPE_LANGUAGE, MODEL_TYPE_IMAGE_TEXT_TO_TEXT

header()
models = get_models(types=[MODEL_TYPE_LANGUAGE, MODEL_TYPE_IMAGE_TEXT_TO_TEXT])
limits = get_limits(models=models, role=st.session_state["user"].role)
limits = [model for model, values in limits.items() if (values["rpd"] is None or values["rpd"] > 0) and (values["rpm"] is None or values["rpm"] > 0)]
models = [model for model in models if model in limits]


@st.dialog(title="Select a document", width="large")
def select_document():
    collections, selected_collection = resources_selector(resource="collection")
    if not collections:
        st.warning(body="First create a collection on the *Documents* page.")
        return

    with st.spinner("Loading documents..."):
        documents, selected_document = resources_selector(resource="document", per_page=10, resource_filter=selected_collection["id"])

    if not documents:
        st.warning(body="No documents found in this collection, please add a document in *Documents* page.")
        return

    with stylable_container(key="Header", css_styles="button{float: right;}"):
        if st.button("**Validate**", key="validate_document"):
            st.session_state["summarize_collection"] = selected_collection
            st.session_state["summarize_document"] = selected_document
            st.rerun()

    return


# Sidebar
with st.sidebar:
    if st.button(label="**:material/refresh: New summarize**", use_container_width=True):
        st.session_state.pop("summarize_collection", None)
        st.session_state.pop("summarize_document", None)
        st.session_state.pop("validate_toc", None)
        st.session_state.pop("toc", None)
        st.session_state.pop("summary", None)
        st.rerun()

    if st.button(label="**:material/description: Select a document**", use_container_width=True):
        select_document()

    st.subheader(body="Summarize parameters")
    selected_model = st.selectbox(label="Language model", options=models)

# Main
st.subheader(body=":material/counter_1: Select a document")
if st.session_state.get("summarize_document"):
    st.info(body=f"Selected document: {st.session_state['summarize_document']['name']} ({st.session_state['summarize_document']['id']})")
else:
    st.info(body="Select a document to summarize.")

## TOC
st.session_state.toc = "" if "toc" not in st.session_state else st.session_state.toc
st.session_state.validate_toc = False if "validate_toc" not in st.session_state else st.session_state.validate_toc

st.markdown(body="***")
st.subheader(body=":material/counter_2: Create a table of content")

if not st.session_state.get("summarize_document"):
    st.stop()
chunks = get_chunks(document_id=st.session_state["summarize_document"]["id"])

st.info(
    body="To help the model generate a summary, you need to write a table of contents for your document. Click on the *generate* button if you need AI assistance."
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
                st.toast(body="You have to write a table of contents before validating it.", icon="❌")


## Summary
st.session_state.summary = "" if "summary" not in st.session_state else st.session_state.summary

st.markdown(body="***")
st.subheader(body=":material/counter_3: Generate a summary")

if not st.session_state.validate_toc:
    st.stop()

st.info(body="Here is the summary of your document.")

st.markdown("**Summary**")
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
            st.toast(body="You have to generate a summary before giving feedback.", icon="❌")
