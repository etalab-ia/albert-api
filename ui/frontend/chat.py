from uuid import uuid4

import streamlit as st

from ui.backend.chat import generate_stream, format_chunk_for_display, get_chunk_full_content, generate_deepsearch_response
from ui.backend.common import get_collections, get_limits, get_models
from ui.backend.document_parsing import (
    parse_document, 
    count_document_characters, 
    extract_text_from_parsed_document,
    process_large_document
)
from ui.frontend.header import header
from ui.variables import MODEL_TYPE_IMAGE_TEXT_TO_TEXT, MODEL_TYPE_LANGUAGE

from ui.configuration import configuration
SEARCH_METHODS = ["multiagent", "hybrid", "semantic", "lexical"]
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
    st.session_state["deepsearch_metadata"] = []  # Nouveau pour stocker les métadonnées DeepSearch

if "document_context" not in st.session_state:
    st.session_state["document_context"] = None

if "auto_created_collection" not in st.session_state:
    st.session_state["auto_created_collection"] = None

# Sidebar
with st.sidebar:
    new_chat = st.button(label="**:material/refresh: New chat**", key="new", use_container_width=True)
    if new_chat:
        st.session_state.pop("messages", None)
        st.session_state.pop("sources", None)
        st.session_state.pop("rag_chunks", None)
        st.session_state.pop("deepsearch_metadata", None)
        st.session_state.pop("document_context", None)
        st.session_state.pop("auto_created_collection", None)
        st.rerun()

    # Section d'upload de document
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
    params = {"sampling_params": {}, "rag_params": {}, "deepsearch_params": {}}

    st.subheader(body="Chat parameters")
    params["sampling_params"]["model"] = st.selectbox(label="Language model", options=models, index=models.index(f"{configuration.playground.default_model}") if f"{configuration.playground.default_model}" in models else 0)
    params["sampling_params"]["temperature"] = st.slider(label="Temperature", value=0.2, min_value=0.0, max_value=1.0, step=0.1)

    max_tokens_active = st.toggle(label="Max tokens", value=None)
    max_tokens = st.number_input(label="Max tokens", value=100, min_value=0, step=100, disabled=not max_tokens_active)
    params["sampling_params"]["max_tokens"] = max_tokens if max_tokens_active else None

    # Section DeepSearch
    st.subheader(body="🌐 WebSearch")
    
    # Toggle DeepSearch simple
    deepsearch = st.toggle(
        label="Activer WebSearch", 
        value=False,
        help=f"Recherche web approfondie avec {params['sampling_params']['model']}"
    )
    
    # Paramètres DeepSearch (visibles seulement si activé)
    if deepsearch:
        with st.expander("⚙️ Paramètres WebSearch", expanded=False):
            params["deepsearch_params"]["k"] = st.number_input(
                label="Résultats par recherche (k)", 
                value=5, 
                min_value=1, 
                max_value=10,
                help="Nombre de résultats à récupérer par requête de recherche"
            )
            params["deepsearch_params"]["iteration_limit"] = st.number_input(
                label="Limite d'itérations", 
                value=2, 
                min_value=1, 
                max_value=5,
                help="Nombre maximum d'itérations de recherche"
            )
            params["deepsearch_params"]["num_queries"] = st.number_input(
                label="Requêtes par itération", 
                value=2, 
                min_value=1, 
                max_value=5,
                help="Nombre de requêtes à générer par itération"
            )
            params["deepsearch_params"]["lang"] = st.selectbox(
                label="Langue", 
                options=["fr", "en"], 
                index=0,
                help="Langue pour la recherche et les réponses"
            )
            
            # Gestion des domaines
            domain_option = st.radio(
                "Restriction de domaines",
                options=["default", "none", "custom"],
                format_func=lambda x: {
                    "default": "🔒 Utiliser la configuration par défaut",
                    "none": "🌐 Tous les domaines autorisés", 
                    "custom": "⚙️ Domaines personnalisés"
                }[x],
                index=0,
                help="Choisir quels domaines autoriser pour la recherche"
            )
            
            if domain_option == "default":
                params["deepsearch_params"]["limited_domains"] = True
                st.caption("Utilise les domaines configurés sur le serveur")
            elif domain_option == "none":
                params["deepsearch_params"]["limited_domains"] = False
            else:  # custom
                custom_domains_text = st.text_area(
                    "Domaines personnalisés (un par ligne)",
                    value="wikipedia.org\nstackoverflow.com\ngithub.com",
                    help="Entrez un domaine par ligne"
                )
                custom_domains = [domain.strip() for domain in custom_domains_text.split("\n") if domain.strip()]
                params["deepsearch_params"]["limited_domains"] = custom_domains
                st.caption(f"Domaines personnalisés: {len(custom_domains)} domaines")

    st.subheader(body="RAG parameters")
    params["rag_params"]["method"] = st.selectbox(label="Search method", options=SEARCH_METHODS, index=0)

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
        params["rag_params"]["k"] = st.number_input(label="Number of chunks to retrieve (k)", value=5)
    else:
        params["rag_params"]["collections"] = []
        params["rag_params"]["k"] = 5

    if st.session_state.selected_collections and not deepsearch:
        rag = st.toggle(label="Activated RAG", value=True, disabled=not bool(params["rag_params"]["collections"]))
    else:
        rag = st.toggle(label="Activated RAG", value=False, disabled=True or deepsearch, help="RAG est désactivé quand WebSearch est activé" if deepsearch else "You need to select at least one collection to activate RAG.")

    # Section discrète pour les statistiques RAG
    if rag and st.session_state.get("rag_chunks"):
        total_chunks = sum(len(chunks) for chunks in st.session_state.rag_chunks if chunks)
        if total_chunks > 0:
            with st.expander("📊 Statistiques RAG", expanded=False):
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

    # Section pour les statistiques DeepSearch
    if deepsearch and st.session_state.get("deepsearch_metadata"):
        metadata_list = [m for m in st.session_state.deepsearch_metadata if m]
        if metadata_list:
            with st.expander("🌐 Statistiques WebSearch", expanded=False):
                total_searches = len(metadata_list)
                total_sources = sum(m.get("sources_found", 0) for m in metadata_list)
                total_time = sum(m.get("elapsed_time", 0) for m in metadata_list)
                total_tokens = sum(m.get("total_input_tokens", 0) + m.get("total_output_tokens", 0) for m in metadata_list)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Recherches effectuées", total_searches)
                    st.metric("Sources trouvées", total_sources)
                with col2:
                    st.metric("Temps total", f"{total_time:.1f}s")
                    st.metric("Tokens utilisés", f"{total_tokens:,}")
                
                if st.button("📋 Détails des recherches"):
                    for i, metadata in enumerate(metadata_list):
                        if metadata:
                            st.write(f"**Recherche {i+1}:**")
                            st.write(f"• Modèle: {metadata.get('model_used', 'N/A')}")
                            st.write(f"• Itérations: {metadata.get('iterations', 'N/A')}")
                            st.write(f"• Requêtes: {metadata.get('total_queries', 'N/A')}")
                            st.write(f"• Temps: {metadata.get('elapsed_time', 0):.1f}s")
                            st.divider()

# Main
with st.chat_message(name="assistant"):
    st.markdown(
        body="""Bonjour je suis Albert, et je peux vous aider si vous avez des questions administratives !

🔍 **Nouvelles capacités disponibles :**
- **WebSearch** : Recherche approfondie sur le web avec plusieurs itérations
- **RAG** : Recherche dans vos bases de connaissances
- **Documents** : Upload direct de documents dans le chat

**Pour utiliser WebSearch :** activez le bouton "Activer WebSearch" dans le menu de gauche pour des recherches web approfondies.

**Pour utiliser RAG :** sélectionnez les collections voulues dans le menu de gauche et activez "Activated RAG".

**Pour les documents :** vous pouvez uploader directement des fichiers qui seront ajoutés au contexte ou converés en collections.

Comment puis-je vous aider ?
"""
    )

for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"], avatar=":material/face:" if message["role"] == "user" else None):
        st.markdown(message["content"])
        
        # Affichage des sources
        if st.session_state.sources[i]:
            st.pills(key=f"sources_{uuid4()}", label="Sources", options=st.session_state.sources[i], label_visibility="hidden")
        
        # Affichage des métadonnées DeepSearch (pour les réponses de l'assistant)
        if (message["role"] == "assistant" and 
            i < len(st.session_state.deepsearch_metadata) and 
            st.session_state.deepsearch_metadata[i]):
            
            metadata = st.session_state.deepsearch_metadata[i]
            with st.expander(f"🌐 Détails WebSearch ({metadata.get('sources_found', 0)} sources)", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Modèle utilisé", metadata.get("model_used", "N/A"))
                    st.metric("Itérations", metadata.get("iterations", "N/A"))
                    st.metric("Requêtes générées", metadata.get("total_queries", "N/A"))
                with col2:
                    st.metric("Temps écoulé", f"{metadata.get('elapsed_time', 0):.2f}s")
                    st.metric("Tokens d'entrée", f"{metadata.get('total_input_tokens', 0):,}")
                    st.metric("Tokens de sortie", f"{metadata.get('total_output_tokens', 0):,}")
        
        # Accès aux chunks RAG (seulement pour les réponses de l'assistant)
        elif (message["role"] == "assistant" and 
              i < len(st.session_state.rag_chunks) and 
              st.session_state.rag_chunks[i]):
            
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
    st.session_state.rag_chunks.append([])
    st.session_state.deepsearch_metadata.append(None)
    
    with st.chat_message(name="user", avatar=":material/face:"):
        st.markdown(body=prompt)

    with st.chat_message(name="assistant"):
        try:
            if deepsearch:
                # Mode DeepSearch
                with st.spinner("🌐 Recherche approfondie en cours..."):
                    response, sources, metadata = generate_deepsearch_response(prompt, params)
                    
                # Afficher la réponse directement (pas de stream pour DeepSearch)
                st.markdown(response)
                
                # Pas de chunks RAG pour DeepSearch
                rag_chunks = []
                
                # Stocker les métadonnées DeepSearch
                st.session_state.deepsearch_metadata[-1] = metadata
                
            else:
                # Mode normal ou RAG
                stream, sources, rag_chunks = generate_stream(
                    messages=messages_to_send,
                    params=params,
                    rag=rag,
                    rerank=False,
                )
                response = st.write_stream(stream=stream)
                
        except Exception as e:
            st.error(body=f"Erreur: {str(e)}")
            st.stop()

        # Formatage et affichage des sources
        formatted_sources = []
        if sources:
            for source in sources:
                if isinstance(source, str):
                    # Pour DeepSearch, les sources sont des URLs
                    if source.lower().startswith("http"):
                        formatted_source = source[:50] + "..." if len(source) > 50 else source
                        formatted_sources.append(f":material/globe: [{formatted_source}]({source})")
                    else:
                        # Pour RAG, les sources sont des noms de documents
                        formatted_source = source[:15] + "..." if len(source) > 15 else source
                        formatted_sources.append(f":material/import_contacts: {formatted_source}")
                        
            if formatted_sources:
                st.pills(label="Sources", options=formatted_sources, label_visibility="hidden")

    # Sauvegarder le message de l'assistant
    assistant_message = {"role": "assistant", "content": response}
    st.session_state.messages.append(assistant_message)
    st.session_state.sources.append(formatted_sources)
    st.session_state.rag_chunks.append(rag_chunks)

with st._bottom:
    st.caption(
        body='<p style="text-align: center;"><i>I can make mistakes, please always verify my sources and answers.</i></p>',
        unsafe_allow_html=True,
    )