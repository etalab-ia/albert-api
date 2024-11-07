import logging
import traceback

from openai import OpenAI
import requests
import streamlit as st

from config import BASE_URL
from utils import get_collections, get_models, header, set_config

# Config
set_config()
API_KEY = header()

# Data
try:
    language_models, embeddings_models = get_models(api_key=API_KEY)
    collections = get_collections(api_key=API_KEY)
except Exception:
    st.error("Error to fetch user data.")
    logging.error(traceback.format_exc())
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
    model_collections = [
        f"{collection["id"]} - {collection["name"]}" for collection in collections if collection["model"] == params["rag"]["embeddings_model"]
    ] + ["internet"]
    if model_collections:
        selected_collections = st.multiselect(label="Collections", options=model_collections, default=[model_collections[0]])
        params["rag"]["collections"] = [collection.split(" - ")[0] for collection in selected_collections]
        params["rag"]["k"] = st.number_input("Top K", value=3)

# Main
col1, col2 = st.columns([0.85, 0.15])
with col1:
    new_chat = st.button("New chat")
with col2:
    if model_collections:
        rag = st.toggle("Activated RAG", value=False, disabled=not bool(params["rag"]["collections"]))
    else:
        rag = st.toggle("Activated RAG", value=False, disabled=True)
if new_chat:
    st.session_state.pop("messages", None)
    st.session_state.pop("sources", None)
    st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.sources = []

for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if st.session_state.sources[i]:
            st.multiselect(options=st.session_state.sources[i], label="Sources", key=f"sources_{i}", default=st.session_state.sources[i])

sources = []
if prompt := st.chat_input("Message to Albert"):
    # send message to the model
    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)
    st.session_state.sources.append([])
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            if rag:
                data = {
                    "collections": params["rag"]["collections"],
                    "model": params["rag"]["embeddings_model"],
                    "k": params["rag"]["k"],
                    "prompt": prompt,
                }
                response = requests.post(f"{BASE_URL}/search", json=data, headers={"Authorization": f"Bearer {API_KEY}"})
                assert response.status_code == 200
                prompt_template = "Réponds à la question suivante en te basant sur les documents ci-dessous : {prompt}\n\nDocuments :\n{chunks}"
                chunks = "\n".join([result["chunk"]["content"] for result in response.json()["data"]])

                sources = list(set(result["chunk"]["metadata"]["document_name"] for result in response.json()["data"]))

                prompt = prompt_template.format(prompt=prompt, chunks=chunks)
                messages = st.session_state.messages[:-1] + [{"role": "user", "content": prompt}]
            else:
                messages = st.session_state.messages
                sources = []

            stream = openai_client.chat.completions.create(stream=True, messages=messages, **params["sampling_params"])
            response = st.write_stream(stream)
        except Exception:
            st.error("Error to generate response.")
            logging.error(traceback.format_exc())
        if sources:
            st.multiselect(options=sources, label="Sources", key="sources_tmp", default=sources)

    assistant_message = {"role": "assistant", "content": response}
    st.session_state.messages.append(assistant_message)
    st.session_state.sources.append(sources)
