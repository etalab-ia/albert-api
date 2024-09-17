from openai import OpenAI
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
