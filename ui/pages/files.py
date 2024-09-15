import time

from streamlit_local_storage import LocalStorage
import streamlit as st
import datetime as dt
import pandas as pd

from config import BASE_URL, DEFAULT_COLLECTION, EMBEDDINGS_MODEL_TYPE, LANGUAGE_MODEL_TYPE, PRIVATE_COLLECTION_TYPE
from utils import delete_file, check_api_key, upload_file, set_config, get_models, get_collections, get_files

set_config()
local_storage = LocalStorage()
key = "albertApiKey"

# Header
col1, col2, col3 = st.columns([0.8, 0.1, 0.1])
with col1:
    st.subheader("Albert playground")

with col3:
    logout = st.button("Logout")
    if logout:
        local_storage.deleteItem(key)
        st.rerun()

# Authentication
API_KEY = local_storage.getItem(key)
if API_KEY is None or not check_api_key(base_url=BASE_URL, api_key=API_KEY):
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

table = []
for collection, file in files.items():
    for i in range(len(file)):
        table.append([
            collection,
            [private_collection["model"] for private_collection in private_collections if private_collection["id"] == collection][0],
            file[i]["id"],
            file[i]["filename"],
            f"{file[i]['bytes'] / (1024 * 1024):.2f} MB",
            dt.datetime.fromtimestamp(file[i]["created_at"]).strftime("%Y-%m-%d"),
        ])

columns = ["Collection", "Embeddings model", "ID", "Name", "Size", "Created at"]
df = pd.DataFrame(table, columns=columns)

# Main
st.markdown("***")
col1, col2 = st.columns(2)

## Upload files
with col1:
    st.subheader("Upload files")
    collection = st.text_input(
        "Collection",
        placeholder=DEFAULT_COLLECTION,
        help="The collection will be created if it does not exist. You can't upload files in a public collection or in a private collection with different embeddings model.",
    )
    embeddings_model = st.selectbox("Embeddings model", embeddings_models)
    file_to_upload = st.file_uploader(f"Choisir un fichier à ajouter à {collection}", type=["pdf", "docx"])
    submit_upload = st.button("Upload")
    if file_to_upload and submit_upload and collection:
        with st.spinner("Téléchargement et traitement du document en cours..."):
            result = upload_file(api_key=API_KEY, file=file_to_upload, embeddings_model=embeddings_model, collection_name=collection)
            time.sleep(0.5)
            st.rerun()

## Delete files
with col2:
    st.subheader("Delete files")
    file_id = st.selectbox("Select file to delete", df["ID"])
    if file_id:
        file_collection = [collection for collection, file in files.items() if file_id in [f["id"] for f in file]][0]
    submit_delete = st.button("Delete")
    if submit_delete:
        delete_file(api_key=API_KEY, collection_name=file_collection, file_id=file_id)
        time.sleep(0.5)
        st.rerun()

## Files
st.subheader("Files")
st.dataframe(df, hide_index=True, use_container_width=True)
