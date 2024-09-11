import streamlit as st
import requests
from openai import OpenAI
import uuid
from streamlit_local_storage import LocalStorage
import time
import os

BASE_URL = "https://albert.api.dev.etalab.gouv.fr/v1"

local_storage = LocalStorage()

def generate_default_collection_name():
    return f"collection_{uuid.uuid4().hex[:8]}"

# Authentification
def authenticate(api_key):
    try:
        client = OpenAI(base_url=BASE_URL, api_key=api_key)
        models = client.models.list()
        if models:
            return client
    except Exception as e:
        st.error(f"Erreur de validation du client : {e}")
        return None

# Récupération des LLMs et embedding models
def get_models(client):
    language_model, embeddings_model = None, None
    print("models:", [model for model in client.models.list().data])
    for model in client.models.list().data:
        if model.type == "text-generation" and language_model is None:
            language_model = model.id
        if model.type == "text-embeddings-inference" and embeddings_model is None:
            embeddings_model = model.id
    # return language_model, embeddings_model
    return "google/gemma-2-9b-it", embeddings_model

@st.cache_data(show_spinner=False)
def upload_document_with_progress(file, api_key, embeddings_model, collection_name):
    url = f"{BASE_URL}/files"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {"collection": collection_name, "embeddings_model": embeddings_model}
    files = {"files": (file.name, file.getvalue(), file.type)}
    
    response = requests.post(url, headers=headers, params=params, files=files)
    
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Erreur lors du téléchargement : {response.text}")
        return None

# Requête RAG
def chat_with_documents(query, client, language_model, embeddings_model, collection_name):
    try:
        data = {
            "model": language_model,
            "messages": [{"role": "user", "content": query}],
            "stream": False,
            "n": 1,
            "tools": [
                {
                    "function": {
                        "name": "BaseRAG",
                        "parameters": {
                            "embeddings_model": embeddings_model,
                            "collections": [collection_name],
                            "k": 2,
                        },
                    },
                    "type": "function",
                }
            ],
        }
        response = client.chat.completions.create(**data)
        return response.choices[0].message.content, response.metadata[0]["BaseRAG"]["prompt"]
    except Exception as e:
        st.error(f"Erreur de chat : {str(e)}")
        st.error(f"Détails de l'erreur : {type(e).__name__}, {e.args}")
        return None, None

# Suppression d'une collection
def delete_collection(api_key, collection_name):
    url = f"{BASE_URL}/collections/{collection_name}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.delete(url, headers=headers)
    if response.status_code == 200:
        return True
    else:
        st.error(f"Erreur lors de la suppression de la collection : {response.text}")
        return False

# Suppression d'un fichier
def delete_file(api_key, collection_name, file_id):
    url = f"{BASE_URL}/files/{collection_name}/{file_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.delete(url, headers=headers)
    if response.status_code == 204:
        return True
    else:
        st.error(f"Erreur lors de la suppression du fichier : {response.text}")
        st.error(f"Code de statut : {response.status_code}")
        st.error(f"Réponse du serveur : {response.text}")
        return False

# Collections d'un user
def get_collections(api_key):
    url = f"{BASE_URL}/collections"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        collections = response.json()["data"]
        
        for collection in collections:
            doc_count = len(list_documents(api_key, collection["id"])) # Compter le nombre de documents dans la collection
            collection["doc_count"] = doc_count
        return collections
    else:
        st.error(f"Erreur lors de la récupération des collections : {response.text}")
        return []

# Liste des documents d'une collection
def list_documents(api_key, collection_name):
    url = f"{BASE_URL}/files/{collection_name}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()["data"]
    elif response.status_code == 404:
        return []
    else:
        st.error(f"Erreur de liste des documents : {response.text}")
        return []

# Sauvegarde de la clé API dans le local storage
def save_api_key(api_key):
    local_storage.setItem("api_key", api_key)

def load_api_key():
    return local_storage.getItem("api_key") or ""

def main():
    st.title("Application de Chat avec Documents")

    # init session state
    if 'client' not in st.session_state:
        st.session_state.client = None
        st.session_state.language_model = None
        st.session_state.embeddings_model = None
        st.session_state.documents_uploaded = False
        st.session_state.collection_name = generate_default_collection_name()
        st.session_state.chat_history = []
    
    if 'files_uploaded' not in st.session_state:
        st.session_state.files_uploaded = []

    # Charger la clé API sauvegardée et essayer de l'authentifier
    saved_api_key = load_api_key()
    if saved_api_key and not st.session_state.client:
        client = authenticate(saved_api_key)
        if client:
            st.session_state.client = client
            print("models riri: ", get_models(client))
            st.session_state.language_model, st.session_state.embeddings_model = get_models(client)
            st.success("Authentification réussie avec la clé API sauvegardée !")
        else:
            st.warning("La clé API sauvegardée est invalide. Veuillez en saisir une nouvelle.")
            local_storage.deleteItem("api_key")  # Si on arrive pas à s'authentifier, on supprime la clé API déjà sauvegardée

    # Affichage pour saisir la clé API si non authentifié   
    if not st.session_state.client:
        api_key = st.text_input("Saisissez votre clé API", type="password", value="")
        if st.button("Connexion"):
            client = authenticate(api_key)
            if client:
                save_api_key(api_key)
                st.session_state.client = client
                st.session_state.language_model, st.session_state.embeddings_model = get_models(client)
                st.success("Authentification réussie !")
                st.rerun()
            else:
                st.error("Clé API invalide")

    if st.session_state.client:
        # Sidebar pour afficher la liste des collections
        st.sidebar.title("Vos Collections")
        
        # Fonction pour charger les collections d'un user
        def load_collections():
            collections = get_collections(load_api_key())
            private_collections = [(c['id'], c['doc_count']) for c in collections if c["type"] == "private"]
            if not private_collections:
                # Créer une collection par défaut si aucune n'existe
                default_collection_name = generate_default_collection_name()
                private_collections = [(default_collection_name, 0)]
            return private_collections

        collections = load_collections()
        
        collection_options = [f"{c[0]} ({c[1]} documents)" for c in collections]
        collection_ids = [c[0] for c in collections]
        
        selected_index = st.sidebar.selectbox(
            "Sélectionnez une collection",
            options=range(len(collection_options)),
            format_func=lambda i: collection_options[i],
            index=0 if collection_options else None,
            key="collection_selector"
        )

        if selected_index is not None:
            st.session_state.collection_name = collection_ids[selected_index]
            
            if st.sidebar.button("Supprimer cette collection", key=f"delete_{st.session_state.collection_name}"):
                if delete_collection(load_api_key(), st.session_state.collection_name):
                    st.sidebar.success(f"Collection '{st.session_state.collection_name}' supprimée avec succès!")
                    # Rafraîchir la liste des collections lorsque la collection est supprimée
                    collections = load_collections()
                    collection_ids = [c[0] for c in collections]
                    if collections:
                        st.session_state.collection_name = collection_ids[0]
                    else:
                        st.session_state.collection_name = generate_default_collection_name()
                    st.rerun()
                else:
                    st.sidebar.error(f"Échec de la suppression de la collection '{st.session_state.collection_name}'")
        else:
            st.session_state.collection_name = generate_default_collection_name()

        st.sidebar.write(f"Collection actuelle : {st.session_state.collection_name}")


        uploaded_file = st.file_uploader("Choisir un fichier à ajouter à la collection", type=["pdf", "docx", "json"])
        if uploaded_file is not None:
            if uploaded_file.name not in st.session_state.files_uploaded:
                with st.spinner('Téléchargement et traitement du document en cours...'):
                    result = upload_document_with_progress(uploaded_file, load_api_key(), st.session_state.embeddings_model, st.session_state.collection_name)
                
                if result:
                    st.success(f"Document '{uploaded_file.name}' téléchargé et vectorisé avec succès !")
                    st.session_state.documents_uploaded = True
                    time.sleep(2)
                    new_collections = load_collections()
                    if new_collections and not collections:
                        # Si c'était la première collection, mettre à jour la collection sélectionnée
                        st.session_state.collection_name = new_collections[0][0]
                    
                    st.session_state.files_uploaded.append(uploaded_file.name)
                    st.rerun()
                else:
                    st.error("Erreur lors du téléchargement ou du traitement du document.")

        # Liste des documents de la collection actuelle
        documents = list_documents(load_api_key(), st.session_state.collection_name)
        if documents:
            st.subheader(f"Documents dans la collection '{st.session_state.collection_name}':")
            for doc in documents:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"- {doc['filename']} (ID: {doc['id']})")
                with col2:
                    if st.button("Supprimer", key=f"delete_{doc['id']}"):
                        with st.spinner(f"Suppression du fichier '{doc['filename']}' en cours..."):
                            if delete_file(load_api_key(), st.session_state.collection_name, doc['id']):
                                st.success(f"Fichier '{doc['filename']}' supprimé avec succès!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"Échec de la suppression du fichier '{doc['filename']}'")
            st.session_state.documents_uploaded = True
        else:
            st.info(f"Aucun document dans la collection '{st.session_state.collection_name}'. Veuillez télécharger un document pour commencer.")
            st.session_state.documents_uploaded = False

        st.subheader("Chat avec les Documents")
        
        # affichage des messages
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        user_input = st.chat_input("Entrez votre question:")
        
        if user_input:
            if not st.session_state.documents_uploaded:
                st.warning("Veuillez d'abord télécharger des documents avant de poser des questions.")
            else:
                # Vérifications supplémentaires
                if not authenticate(load_api_key()):
                    st.error("La clé API n'est plus valide. Veuillez vous reconnecter.")
                    return
                
                documents = list_documents(load_api_key(), st.session_state.collection_name)
                if not documents:
                    st.warning("La collection est vide. Veuillez ajouter des documents avant de poser des questions.")
                    return
                
                # st.write(f"Modèle de langage : {st.session_state.language_model}")
                # st.write(f"Modèle d'embeddings : {st.session_state.embeddings_model}")
                # st.write(f"Nom de la collection : {st.session_state.collection_name}")

                st.session_state.chat_history.append({"role": "user", "content": user_input})
                with st.chat_message("user"):
                    st.markdown(user_input)

                response, prompt = chat_with_documents(user_input, st.session_state.client, 
                                                       st.session_state.language_model, 
                                                       st.session_state.embeddings_model,
                                                       st.session_state.collection_name)
                
                if response:
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                    with st.chat_message("assistant"):
                        st.markdown(response)
                    with st.expander("Afficher le prompt RAG"):
                        st.text(prompt)
                else:
                    st.warning("Une erreur s'est produite lors de la génération de la réponse.")
        elif not st.session_state.documents_uploaded:
            st.info("Téléchargez des documents pour commencer à poser des questions.")


if __name__ == "__main__":
    main()