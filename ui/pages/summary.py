from uuid import uuid4

import streamlit as st

from utils import create_collection, get_documents, header, set_config, upload_file


# Config
set_config()
API_KEY = header()


st.title("Générateur de résumé de documents")

# Initialisation des variables d'état de session
if "step" not in st.session_state:
    st.session_state.step = "upload"


# Étape 1: Téléchargement et extraction du texte
if st.session_state.step == "upload":
    st.header("Étape 1: Téléchargement du document")
    uploaded_file = st.file_uploader("Choisissez un fichier", type=["pdf", "docx", "txt"])

    if uploaded_file is not None:
        st.session_state.collection_id = f"temp_{uuid4().hex}"
        collection_id = create_collection(
            api_key=API_KEY, collection_model="intfloat/multilingual-e5-large", collection_name=st.session_state.collection_id
        )
        upload_file(api_key=API_KEY, file=uploaded_file, collection_id=collection_id)
        documents = get_documents(api_key=API_KEY, collection_ids=[st.session_state.collection_id])
        print(documents, flush=True)
