import datetime as dt
import time

import pandas as pd
import streamlit as st

from utils import delete_file, get_collections, get_files, get_models, header, set_config, upload_file

# Config
set_config()
API_KEY = header()

# Data
try:
    language_models, embeddings_models = get_models(api_key=API_KEY)
    collections = get_collections(api_key=API_KEY)
    file_data = get_files(api_key=API_KEY, collections=[collection["id"] for collection in collections])
except Exception as e:
    st.error("Error to fetch user data.")
    st.stop()

table = []
for collection_name, files in file_data.items():
    for file in files:
        table.append(
            [
                collection_name,
                [collection["model"] for collection in collections if collection["id"] == collection_name][0],
                file["id"],
                file["file_name"],
                f"{file['bytes'] / (1024 * 1024):.2f} MB",
                dt.datetime.fromtimestamp(file["created_at"]).strftime("%Y-%m-%d"),
            ]
        )

columns = ["Collection", "Embeddings model", "ID", "Name", "Size", "Created at"]
df = pd.DataFrame(table, columns=columns)

# Main
col1, col2 = st.columns(2)

## Upload files
with col1:
    st.subheader("Upload files")
    collection = st.text_input(
        "Collection",
        placeholder="Mes documents",
        help="The collection will be created if it does not exist. You can't upload files in a public collection or in a private collection with different embeddings model.",
    )
    embeddings_model = st.selectbox("Embeddings model", embeddings_models)
    file_to_upload = st.file_uploader(f"Choisir un fichier à ajouter à {collection}", type=["pdf", "docx"])
    submit_upload = st.button("Upload", disabled=not collection or not file_to_upload)
    if file_to_upload and submit_upload and collection_name:
        with st.spinner("Téléchargement et traitement du document en cours..."):
            result = upload_file(api_key=API_KEY, file=file_to_upload, embeddings_model=embeddings_model, collection_name=collection)
            time.sleep(0.5)
            st.rerun()

## Delete files
with col2:
    st.subheader("Delete files")
    file_id = st.selectbox("Select file to delete", df["ID"])
    if file_id:
        file_collection = [collection_name for collection_name, file in file_data.items() if file_id in [f["id"] for f in file]][0]
    submit_delete = st.button("Delete", disabled=not file_id)
    if submit_delete:
        delete_file(api_key=API_KEY, collection_name=file_collection, file_id=file_id)
        time.sleep(0.5)
        st.rerun()

## Files
st.subheader("Files")
st.dataframe(df, hide_index=True, use_container_width=True)
