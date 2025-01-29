import datetime as dt
import time
from typing import List, Tuple

from openai import OpenAI
import pandas as pd
import requests
import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from config import (
    AUDIO_MODEL_TYPE,
    BASE_URL,
    CACHE_DURATION_IN_SECONDS,
    EMBEDDINGS_MODEL_TYPE,
    INTERNET_COLLECTION_DISPLAY_ID,
    LANGUAGE_MODEL_TYPE,
    PRIVATE_COLLECTION_TYPE,
    RERANK_MODEL_TYPE,
)


def header() -> str:
    def check_api_key(base_url: str, api_key: str) -> bool:
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(url=base_url.replace("/v1", "/health"), headers=headers)

        return response.status_code == 200

    def authenticate():
        API_KEY = st.session_state.get("API_KEY")
        if API_KEY is None:
            with st.form(key="my_form"):
                API_KEY = st.text_input(label="Please enter your API key", type="password")
                submit = st.form_submit_button(label="Submit")
                if submit:
                    if check_api_key(base_url=BASE_URL, api_key=API_KEY):
                        st.session_state["API_KEY"] = API_KEY
                        st.toast("Authentication succeed", icon="✅")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.toast("Please enter a correct API key", icon="❌")
                        st.stop()
                else:
                    st.stop()

        return API_KEY

    with stylable_container(
        key="Header",
        css_styles="""
        button{
            float: right;
            
        }
    """,
    ):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Albert playground")

        # Authentication
        API_KEY = authenticate()
        with col2:
            logout = st.button("Logout")
        if logout:
            st.session_state.pop("API_KEY")
            st.rerun()
        st.markdown("***")

    return API_KEY


def refresh_all_data(api_key: str) -> None:
    get_models.clear(api_key)
    get_collections.clear(api_key)
    get_documents.clear(api_key)


@st.cache_data(show_spinner=False, ttl=CACHE_DURATION_IN_SECONDS)
def get_models(api_key: str) -> tuple[str, str, str]:
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{BASE_URL}/models", headers=headers)
    assert response.status_code == 200, f"{response.status_code} - {response.json()}"
    models = response.json()["data"]
    embeddings_models = sorted([model["id"] for model in models if model["type"] == EMBEDDINGS_MODEL_TYPE and model["status"] == "available"])
    language_models = sorted([model["id"] for model in models if model["type"] == LANGUAGE_MODEL_TYPE and model["status"] == "available"])
    audio_models = sorted([model["id"] for model in models if model["type"] == AUDIO_MODEL_TYPE and model["status"] == "available"])
    rerank_models = sorted([model["id"] for model in models if model["type"] == RERANK_MODEL_TYPE and model["status"] == "available"])
    return language_models, embeddings_models, audio_models, rerank_models


# Collections


@st.cache_data(show_spinner="Retrieving data...", ttl=CACHE_DURATION_IN_SECONDS)
def get_collections(api_key: str) -> list:
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{BASE_URL}/collections", headers=headers)
    assert response.status_code == 200, f"{response.status_code} - {response.json()}"
    collections = response.json()["data"]

    for collection in collections:
        if collection["id"] == INTERNET_COLLECTION_DISPLAY_ID:
            collection["name"] = "Internet"

    return collections


def create_collection(api_key: str, collection_name: str, collection_model: str) -> None:
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.post(f"{BASE_URL}/collections", json={"name": collection_name, "model": collection_model}, headers=headers)
    if response.status_code == 201:
        st.toast("Create succeed", icon="✅")
        # clear cache
        get_collections.clear(api_key)
    else:
        st.toast("Create failed", icon="❌")


def delete_collection(api_key: str, collection_id: str) -> None:
    url = f"{BASE_URL}/collections/{collection_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.delete(url, headers=headers)
    if response.status_code == 204:
        st.toast("Delete succeed", icon="✅")
        # clear cache
        get_collections.clear(api_key)
    else:
        st.toast("Delete failed", icon="❌")


# Documents


def upload_file(api_key: str, file, collection_id: str) -> None:
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"file": (file.name, file.getvalue(), file.type)}
    data = {"request": '{"collection": "%s"}' % collection_id}
    response = requests.post(f"{BASE_URL}/files", data=data, files=files, headers=headers)

    if response.status_code == 201:
        st.toast("Upload succeed", icon="✅")
        # clear cache
        get_collections.clear(api_key)  # since the number of documents in the collection has changed
        get_documents.clear(api_key)
    else:
        st.toast("Upload failed", icon="❌")


@st.cache_data(show_spinner="Retrieving data...", ttl=CACHE_DURATION_IN_SECONDS)
def get_documents(api_key: str, collection_ids: List[str]) -> dict:
    documents = list()
    headers = {"Authorization": f"Bearer {api_key}"}
    for collection_id in collection_ids:
        response = requests.get(f"{BASE_URL}/documents/{collection_id}", headers=headers)
        assert response.status_code == 200, f"{response.status_code} - {response.json()}"
        data = response.json()["data"]
        for document in data:
            document["collection_id"] = collection_id
            documents.append(document)

    return documents


def delete_document(api_key: str, collection_id: str, document_id: str) -> None:
    url = f"{BASE_URL}/documents/{collection_id}/{document_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.delete(url, headers=headers)
    if response.status_code == 204:
        st.toast("Delete succeed", icon="✅")
        # clear cache
        get_documents.clear(api_key)
    else:
        st.toast("Delete failed", icon="❌")


# Load everything


def load_data(api_key: str):
    try:
        _, embeddings_models, _, _ = get_models(api_key=api_key)
        collections = get_collections(api_key=api_key)
        collections = [collection for collection in collections if collection["id"] != INTERNET_COLLECTION_DISPLAY_ID]
        documents = get_documents(
            api_key=api_key,
            collection_ids=[collection["id"] for collection in collections if collection["type"] == PRIVATE_COLLECTION_TYPE],
        )
    except Exception as e:
        st.error("Error to fetch user data.")
        st.stop()

    # collections
    data = [
        {
            "ID": collection["id"],
            "Name": collection["name"],
            "Type": collection["type"],
            "Model": collection["model"],
            "Documents": collection["documents"],
        }
        for collection in collections
    ]
    columns = ["ID", "Name", "Type", "Model", "Documents"]
    df_collections = pd.DataFrame(data, columns=columns)

    # documents
    data = [
        {
            "Collection": document["collection_id"],
            "ID": document["id"],
            "Name": document["name"],
            "Created at": dt.datetime.fromtimestamp(document["created_at"]).strftime("%Y-%m-%d"),
            "Chunks": document["chunks"],
        }
        for document in documents
    ]
    columns = ["Collection", "ID", "Name", "Created at", "Chunks"]
    df_files = pd.DataFrame(data, columns=columns)

    return embeddings_models, collections, documents, df_collections, df_files


# Chat


def generate_stream(messages: List[dict], params: dict, api_key: str, rag: bool, rerank: bool) -> Tuple[str, List[str]]:
    sources = []
    if rag:
        prompt = messages[-1]["content"]
        k = params["rag"]["k"] * 2 if rerank else params["rag"]["k"]
        data = {"collections": params["rag"]["collections"], "k": k, "prompt": messages[-1]["content"], "score_threshold": None}
        response = requests.post(f"{BASE_URL}/search", json=data, headers={"Authorization": f"Bearer {api_key}"})
        assert response.status_code == 200, f"{response.status_code} - {response.json()}"

        prompt_template = """Réponds à la question suivante de manière claire en te basant sur les extraits de documents ci-dessous. Si les documents ne sont pas pertinents pour répondre à la question, réponds que tu ne sais pas ou réponds directement la question à l'aide de tes connaissances. Réponds en français.
La question de l'utilisateur est : {prompt}

Les documents sont :

{chunks}
"""
        chunks = [chunk["chunk"] for chunk in response.json()["data"]]

        if rerank:
            data = {
                "model": params["rag"]["rerank_model"],
                "prompt": prompt,
                "input": [chunk["content"] for chunk in chunks],
            }
            response = requests.post(f"{BASE_URL}/rerank", json=data, headers={"Authorization": f"Bearer {api_key}"})
            assert response.status_code == 200, f"{response.status_code} - {response.json()}"

            rerank_scores = sorted(response.json()["data"], key=lambda x: x["score"])
            chunks = [chunks[result["index"]] for result in rerank_scores[: params["rag"]["k"]]]

        sources = [chunk["metadata"]["document_name"] for chunk in chunks]
        chunks = [chunk["content"] for chunk in chunks]
        prompt = prompt_template.format(prompt=prompt, chunks="\n\n".join(chunks))
        messages = messages[:-1] + [{"role": "user", "content": prompt}]

    client = OpenAI(base_url=BASE_URL, api_key=api_key)
    stream = client.chat.completions.create(stream=True, messages=messages, **params["sampling_params"])

    return stream, sources
