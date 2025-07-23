
from uuid import uuid4

import streamlit as st

from ui.backend.chat import (
    generate_stream, 
    format_chunk_for_display, 
    get_chunk_full_content,
    check_deepsearch_status,
    format_deepsearch_metadata
)
from ui.backend.common import get_collections, get_limits, get_models
from ui.backend.document_parsing import (
    parse_document, 
    count_document_characters, 
    extract_text_from_parsed_document,
    process_large_document
)
from ui.frontend.header import header
from ui.variables import MODEL_TYPE_IMAGE_TEXT_TO_TEXT, MODEL_TYPE_LANGUAGE

SEARCH_METHODS = ["multiagent", "hybrid", "semantic", "lexical", "deepsearch"]  # AJOUT de deepsearch
header()

# Data
models = get_models(types=[MODEL_TYPE_LANGUAGE, MODEL_TYPE_IMAGE_TEXT_TO_TEXT])
limits = get_limits(models=models, role=st.session_state["user"].role)
limits = [model for model, values in limits.items() if (values["rpd"] is None or values["rpd"] > 0) and (values["rpm"] is None or values["rpm"] > 0)]
models = [model for model in models if model in limits]
collections = get_collections()

# State
if "selected_collections" not in st.session_state:
    st.session_state.selected_collections = []

if "messages" not in st.session_state:
    st.session_state["messages"] = []
    st.session_state["sources"] = []
    st.session_state["rag_chunks"] = []  

if "document_context" not in st.session_state:
    st.session_state["document_context"] = None

if "auto_created_collection" not in st.session_state:
    st.session_state["auto_created_collection"] = None

if "deepsearch_metadata" not in st.session_state:
    st.session_state["deepsearch_metadata"] = []

# Sidebar
with st.sidebar:
    new_chat = st.button(label="**:material/refresh: New chat**", key="new", use_container_width=True)
    if new_chat:
        st.session_state.pop("messages", None)
        st.session_state.pop("sources", None)
        st.session_state.pop("rag_chunks", None)  # Nettoyer les chunks aussi
        st.session_state.pop("document_context", None)
        st.session_state.pop("auto_created_collection", None)
        st.session_state.pop("deepsearch_metadata", None)
        st.rerun()

    # Section d'upload de document (inchangée)
    st.subheader("📄 Document")
    uploaded_file = st.file_uploader(
        "Ajouter un document au chat",
        type=['pdf', 'txt', 'md', 'html', 'htm'],
        help="Les documents < 10k caractères seront ajoutés directement au contexte. Les plus volumineux créeront une collection."
    )
    
    if uploaded_file is not None:
        if st.button("🔄 Traiter le document", use_container_width=True):
            try:
                # Parse le document
                with st.spinner("Parsing du document..."):
                    parsed_document = parse_document(uploaded_file)
                    char_count = count_document_characters(parsed_document)
                
                if char_count < 10000:
                    # Ajouter au contexte direct
                    document_text = extract_text_from_parsed_document(parsed_document)
                    st.session_state["document_context"] = {
                        "filename": uploaded_file.name,
                        "content": document_text,
                        "char_count": char_count
                    }
                    st.success(f"✅ Document '{uploaded_file.name}' ajouté au contexte ({char_count:,} caractères)")
                
                else:
                    # Créer collection et uploader
                    with st.spinner("Création de la collection et upload..."):
                        collection_id = process_large_document(uploaded_file, char_count)
                        if collection_id:
                            st.session_state["auto_created_collection"] = collection_id
                            # Ajouter automatiquement à la sélection
                            if collection_id not in st.session_state.selected_collections:
                                st.session_state.selected_collections.append(collection_id)
                            st.success(f"✅ Document volumineux traité - Collection créée ({char_count:,} caractères)")
                            st.rerun()
                        else:
                            st.error("❌ Erreur lors de la création de la collection")
            
            except Exception as e:
                st.error(f"❌ Erreur: {str(e)}")

    # Affichage du contexte actuel
    if st.session_state.get("document_context"):
        with st.expander("📄 Document en contexte"):
            doc_info = st.session_state["document_context"]
            st.write(f"**Fichier:** {doc_info['filename']}")
            st.write(f"**Caractères:** {doc_info['char_count']:,}")
            if st.button("🗑️ Retirer du contexte"):
                st.session_state.pop("document_context", None)
                st.rerun()

    # Initialize params structure
    params = {"sampling_params": {}, "rag_params": {}}

    st.subheader(body="Chat parameters")
    params["sampling_params"]["model"] = st.selectbox(label="Language model", options=models)
    params["sampling_params"]["temperature"] = st.slider(label="Temperature", value=0.2, min_value=0.0, max_value=1.0, step=0.1)

    max_tokens_active = st.toggle(label="Max tokens", value=None)
    max_tokens = st.number_input(label="Max tokens", value=100, min_value=0, step=100, disabled=not max_tokens_active)
    params["sampling_params"]["max_tokens"] = max_tokens if max_tokens_active else None

    st.subheader(body="RAG parameters")

    
    params["rag_params"]["method"] = st.selectbox(
        label="Search method", 
        options=SEARCH_METHODS,  # Garde toutes les méthodes y compris deepsearch
        index=0,
        help="DeepSearch = recherche web approfondie avec domaines configurés"
    )

    if params["rag_params"]["method"] == "deepsearch":
        with st.expander("🔍 Paramètres DeepSearch", expanded=True):
            # Sélecteur de modèle spécifique pour DeepSearch
            st.write("**🤖 Modèle pour DeepSearch**")
            params["rag_params"]["deepsearch_model"] = st.selectbox(
                "Modèle DeepSearch",
                options=models,
                index=models.index(params["sampling_params"]["model"]) if params["sampling_params"]["model"] in models else 0,
                help="Modèle utilisé pour la génération de requêtes, évaluation et synthèse",
                key="deepsearch_model_selector"
            )
            
            st.divider()
            
            # Information sur les domaines
            st.info("🔒 **Domaines de recherche :** Configuration par défaut (domaines restreints depuis config.yml)")
            
            # Paramètres de recherche
            col1, col2 = st.columns(2)
            with col1:
                params["rag_params"]["iteration_limit"] = st.number_input(
                    "Itérations max", 
                    value=2, 
                    min_value=1, 
                    max_value=5,
                    help="Nombre maximum d'itérations de recherche"
                )
                params["rag_params"]["k"] = st.number_input(
                    "Résultats par requête", 
                    value=5, 
                    min_value=1, 
                    max_value=10,
                    help="Nombre de pages web par requête de recherche"
                )
            with col2:
                params["rag_params"]["num_queries"] = st.number_input(
                    "Requêtes par itération", 
                    value=2, 
                    min_value=1, 
                    max_value=5,
                    help="Nombre de requêtes générées par itération"
                )
                params["rag_params"]["lang"] = st.selectbox(
                    "Langue", 
                    options=["fr", "en"], 
                    index=0,
                    help="Langue pour la recherche et génération"
                )
        
        # Note d'information pour DeepSearch
        st.info(f"🌐 **DeepSearch** avec **{params['rag_params']['deepsearch_model']}** - Recherche web sur domaines configurés")
        
    else:
        # Paramètres RAG classiques
        if collections:
            @st.dialog(title="Select collections")
            def add_collection(collections: list) -> None:
                selected_collections = st.session_state.selected_collections
                col1, col2 = st.columns(spec=2)

                for collection in collections:
                    # Marquer la collection auto-créée
                    collection_label = f"{collection['name']} ({collection['id']})"
                    if collection['id'] == st.session_state.get("auto_created_collection"):
                        collection_label += " 🤖"
                    
                    if st.checkbox(
                        label=collection_label,
                        value=False if collection["id"] not in st.session_state.selected_collections else True,
                    ):
                        if collection["id"] not in selected_collections:
                            selected_collections.append(collection["id"])
                    elif collection["id"] in selected_collections:
                        selected_collections.remove(collection["id"])

                with col1:
                    if st.button(label="**Submit :material/check_circle:**", use_container_width=True):
                        st.session_state.selected_collections = list(set(selected_collections))
                        st.rerun()
                with col2:
                    if st.button(label="**Clear :material/close:**", use_container_width=True):
                        st.session_state.selected_collections = []
                        st.rerun()

            option_map = {0: f"{len(set(st.session_state.selected_collections))} selected"}
            pill = st.pills(
                label="Collections",
                options=option_map.keys(),
                format_func=lambda option: option_map[option],
                selection_mode="single",
                default=None,
                key="add_collections",
            )
            if pill == 0:
                add_collection(collections=collections)

            params["rag_params"]["collections"] = st.session_state.selected_collections
            if "k" not in params["rag_params"]:  # Éviter d'écraser si DeepSearch
                params["rag_params"]["k"] = st.number_input(label="Number of chunks to retrieve (k)", value=5)
        else:
            params["rag_params"]["collections"] = []
            if "k" not in params["rag_params"]:
                params["rag_params"]["k"] = 5

    # Gestion de l'activation RAG
    if params["rag_params"]["method"] == "deepsearch":
        rag = st.toggle(label="Activated DeepSearch", value=True, help="DeepSearch effectue une recherche web avec les domaines configurés.")
    else:
        if st.session_state.selected_collections:
            rag = st.toggle(label="Activated RAG", value=True, disabled=not bool(params["rag_params"]["collections"]))
        else:
            rag = st.toggle(label="Activated RAG", value=False, disabled=True, help="You need to select at least one collection to activate RAG.")
    # Section discrète pour les statistiques RAG/DeepSearch
    if rag and (st.session_state.get("rag_chunks") or st.session_state.get("deepsearch_metadata")):
        with st.expander("📊 Statistiques", expanded=False):
            # Stats RAG classiques
            if st.session_state.get("rag_chunks"):
                total_chunks = sum(len(chunks) for chunks in st.session_state.rag_chunks if chunks)
                if total_chunks > 0:
                    st.metric("Total chunks utilisés", total_chunks)
                    st.metric("Messages avec RAG", len([c for c in st.session_state.rag_chunks if c]))
                    
                    # Répartition par document
                    doc_usage = {}
                    for chunks in st.session_state.rag_chunks:
                        for chunk in chunks:
                            doc_name = chunk.get("document_name", "Unknown")
                            doc_usage[doc_name] = doc_usage.get(doc_name, 0) + 1
                    
                    if doc_usage:
                        st.write("**Utilisation par document :**")
                        for doc, count in sorted(doc_usage.items(), key=lambda x: x[1], reverse=True):
                            st.write(f"• {doc}: {count} chunks")
            
            # Stats DeepSearch
            if st.session_state.get("deepsearch_metadata"):
                st.divider()
                total_searches = len(st.session_state.deepsearch_metadata)
                total_time = sum(m['elapsed_time'] for m in st.session_state.deepsearch_metadata)
                total_tokens = sum(m['total_input_tokens'] + m['total_output_tokens'] for m in st.session_state.deepsearch_metadata)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Recherches DeepSearch", total_searches)
                with col2:
                    st.metric("Temps total", f"{total_time:.1f}s")
                with col3:
                    st.metric("Tokens total", f"{total_tokens:,}")

# Main
with st.chat_message(name="assistant"):
    st.markdown(
        body="""Bonjour je suis Albert, et je peux vous aider si vous avez des questions administratives !

**Options disponibles :**
- 📚 **RAG classique** : Recherche dans vos collections de documents
- 🌐 **DeepSearch** : Recherche web approfondie avec analyse intelligente
- 📄 **Upload direct** : Ajout de documents au contexte

Sélectionnez votre méthode de recherche dans le menu de gauche.
                
Comment puis-je vous aider ?
"""
    )

for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"], avatar=":material/face:" if message["role"] == "user" else None):
        st.markdown(message["content"])
        
        # Affichage des sources
        if st.session_state.sources[i]:
            st.pills(key=f"sources_{uuid4()}", label="Sources", options=st.session_state.sources[i], label_visibility="hidden")
        
        # Affichage spécialisé selon le type de recherche
        if message["role"] == "assistant":
            # Chunks RAG classiques
            if i < len(st.session_state.rag_chunks) and st.session_state.rag_chunks[i]:
                chunks = st.session_state.rag_chunks[i]
                
                with st.expander(f"🔍 Détails RAG ({len(chunks)} chunks utilisés)", expanded=False):
                    
                    # Onglets pour différentes vues
                    tab1, tab2 = st.tabs(["📋 Aperçu", "📄 Contenu complet"])
                    
                    with tab1:
                        st.write("**Chunks utilisés dans cette réponse :**")
                        for idx, chunk in enumerate(chunks):
                            st.markdown(format_chunk_for_display(chunk, idx))
                            st.divider()
                    
                    with tab2:
                        chunk_selector = st.selectbox(
                            "Sélectionner un chunk à examiner",
                            range(len(chunks)),
                            format_func=lambda x: f"Chunk {x+1}: {chunks[x]['document_name'][:30]}...",
                            key=f"chunk_selector_{i}"
                        )
                        
                        if chunk_selector is not None:
                            st.markdown(get_chunk_full_content(chunks[chunk_selector]))
            
            # Métadonnées DeepSearch
            elif i < len(st.session_state.get("deepsearch_metadata", [])):
                metadata = st.session_state.deepsearch_metadata[i]
                
                with st.expander("🌐 Métadonnées DeepSearch", expanded=False):
                    st.markdown(format_deepsearch_metadata(metadata))

sources = []
if prompt := st.chat_input(placeholder="Message to Albert"):
    # Préparer les messages en incluant le contexte du document si présent
    messages_to_send = st.session_state.messages.copy()
    
    # Ajouter le contexte du document si présent
    if st.session_state.get("document_context"):
        doc_context = st.session_state["document_context"]
        system_message = {
            "role": "system", 
            "content": f"Document '{doc_context['filename']}' est disponible dans le contexte:\n\n{doc_context['content']}"
        }
        # Insérer au début si pas déjà présent
        if not messages_to_send or messages_to_send[0].get("role") != "system":
            messages_to_send.insert(0, system_message)
        else:
            # Remplacer le message système existant
            messages_to_send[0] = system_message
    
    # Ajouter le message utilisateur
    user_message = {"role": "user", "content": prompt}
    messages_to_send.append(user_message)
    
    # Sauvegarder pour l'affichage (sans le contexte système)
    st.session_state.messages.append(user_message)
    st.session_state.sources.append([])
    st.session_state.rag_chunks.append([])  # Initialiser les chunks pour ce message
    
    with st.chat_message(name="user", avatar=":material/face:"):
        st.markdown(body=prompt)

    with st.chat_message(name="assistant"):
        try:
            # Différencier l'affichage selon le type de recherche
            if rag and params["rag_params"]["method"] == "deepsearch":
                # DeepSearch : réponse directe avec indicateur de progression
                with st.spinner("🌐 Recherche web approfondie en cours..."):
                    response, sources, rag_chunks = generate_stream(
                        messages=messages_to_send,
                        params=params,
                        rag=rag,
                        rerank=False,
                    )
                # Afficher la réponse directement
                st.markdown(response)
            else:
                # RAG classique : stream normal
                stream, sources, rag_chunks = generate_stream(
                    messages=messages_to_send,
                    params=params,
                    rag=rag,
                    rerank=False,
                )
                response = st.write_stream(stream=stream)
        except Exception as e:
            st.error(body=e)
            st.stop()

        formatted_sources = []
        if sources:
            for source in sources:
                formatted_source = source[:50] + "..." if len(source) > 50 else source
                if source.lower().startswith("http"):
                    formatted_sources.append(f":material/globe: [{formatted_source}]({source})")
                else:
                    formatted_sources.append(f":material/import_contacts: {formatted_source}")
            st.pills(label="Sources", options=formatted_sources, label_visibility="hidden")

    assistant_message = {"role": "assistant", "content": response}
    st.session_state.messages.append(assistant_message)
    st.session_state.sources.append(formatted_sources)
    st.session_state.rag_chunks.append(rag_chunks)  # Stocker les chunks détaillés

with st._bottom:
    st.caption(
        body='<p style="text-align: center;"><i>I can make mistakes, please always verify my sources and answers.</i></p>',
        unsafe_allow_html=True,
    )