import time

import streamlit as st
from config import (
    BASE_URL,
    DEFAULT_COLLECTION,
    EMBEDDINGS_MODEL_TYPE,
    LANGUAGE_MODEL_TYPE,
    PRIVATE_COLLECTION_TYPE,
)
from openai import OpenAI
from streamlit_local_storage import LocalStorage
from utils import check_api_key, get_collections, get_files, get_models, set_config

set_config()
local_storage = LocalStorage()
key = "albertApiKey"

col1, col2, col3 = st.columns([0.8, 0.1, 0.1])
with col1:
    st.subheader("Albert playground")

# Authentication
with col3:
    logout = st.button("Logout")
    if logout:
        local_storage.deleteItem(key)
        st.rerun()

API_KEY = local_storage.getItem(key)
if API_KEY is None:
    with st.form(key="my_form"):
        API_KEY = st.text_input(label="Please enter your API key", type="password")
        submit = st.form_submit_button(label="Submit")
        if submit:
            session = {}
            if check_api_key(base_url=BASE_URL, api_key=API_KEY):
                local_storage.setItem(key, API_KEY)
                st.toast("Authentication succeed", icon="✅")
                time.sleep(0.5)
                st.rerun()
            else:
                st.toast("Please enter a correct API key", icon="❌")
        else:
            st.stop()
try:
    models = get_models(api_key=API_KEY)
    embeddings_models = [model["id"] for model in models if model["type"] == EMBEDDINGS_MODEL_TYPE]
    language_models = [model["id"] for model in models if model["type"] == LANGUAGE_MODEL_TYPE]

    collections = get_collections(api_key=API_KEY)
    private_collections = [collection for collection in collections if collection["type"] == PRIVATE_COLLECTION_TYPE]
    private_collection_names = [collection["id"] for collection in private_collections]
    files = get_files(api_key=API_KEY, collections=private_collection_names) if private_collections else {}
except Exception as e:
    st.error(f"Error to fetch user data: {e}")
    st.stop()

openai_client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# Sidebar
with st.sidebar:
    st.title("Model parameters")
    params = {"sampling_params": dict(), "rag": dict()}

    params["sampling_params"]["model"] = st.selectbox("Language model", language_models)
    params["sampling_params"]["temperature"] = st.number_input("Temperature", value=0.1)
    params["sampling_params"]["max_tokens"] = st.number_input("Max tokens (optional)", value=400)

    st.title("RAG parameters")
    params["rag"]["embeddings_model"] = st.selectbox("Embeddings model", embeddings_models)
    model_collections = [collection["id"] for collection in collections if collection["model"] == params["rag"]["embeddings_model"]]
    if model_collections:
        params["rag"]["collections"] = st.multiselect(label="Collections", options=model_collections, default=[model_collections[0]])
        collection_files = [file for collection in params["rag"]["collections"] for file in files[collection]]
        file_names = [file["filename"] for file in collection_files]
        selected_file_names = st.multiselect(
            label="Files",
            options=file_names,
            default=[file_names[0]],
            disabled=not bool(files) or DEFAULT_COLLECTION not in params["rag"]["collections"],
        )
        params["rag"]["file_ids"] = (
            [file["id"] for file in collection_files if file["filename"] in selected_file_names] if selected_file_names else None
        )
        params["rag"]["k"] = st.number_input("Top K", value=3)

# Main app
st.markdown("***")

## Chat
col1, col2 = st.columns([0.85, 0.15])
with col1:
    new_chat = st.button("New chat")
with col2:
    if model_collections:
        rag = st.toggle("Activated RAG", value=False, disabled=not bool(params["rag"]["collections"]))
    else:
        rag = st.toggle("Activated RAG", value=False, disabled=True)
if new_chat:
    st.session_state.clear()
    st.rerun()
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Message to Albert"):
    # send message to the model
    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if rag:
            params["sampling_params"]["tools"] = [{"function": {"name": "BaseRAG", "parameters": params["rag"]}, "type": "function"}]
        stream = openai_client.chat.completions.create(stream=True, messages=st.session_state.messages, **params["sampling_params"])
        response = st.write_stream(stream)

    assistant_message = {"role": "assistant", "content": response}
    st.session_state.messages.append(assistant_message)
