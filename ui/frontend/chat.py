from uuid import uuid4

import streamlit as st

from ui.backend.chat import generate_stream
from ui.backend.common import get_collections, get_limits, get_models
from ui.frontend.header import header
from ui.variables import MODEL_TYPE_IMAGE_TEXT_TO_TEXT, MODEL_TYPE_LANGUAGE

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

# Sidebar
with st.sidebar:
    new_chat = st.button(label="**:material/refresh: New chat**", key="new", use_container_width=True)
    if new_chat:
        st.session_state.pop("messages", None)
        st.session_state.pop("sources", None)
        st.rerun()

    # Initialize params structure
    # sampling_params for LLM model, temperature, etc.
    # rag_params for collections, k, method for search.
    params = {"sampling_params": {}, "rag_params": {}}

    st.subheader(body="Chat parameters")
    params["sampling_params"]["model"] = st.selectbox(label="Language model", options=models)
    # Search method moved to RAG parameters section
    params["sampling_params"]["temperature"] = st.slider(label="Temperature", value=0.2, min_value=0.0, max_value=1.0, step=0.1)

    max_tokens_active = st.toggle(label="Max tokens", value=None)
    max_tokens = st.number_input(label="Max tokens", value=100, min_value=0, step=100, disabled=not max_tokens_active)
    params["sampling_params"]["max_tokens"] = max_tokens if max_tokens_active else None

    st.subheader(body="RAG parameters")
    # Search method selection now under RAG parameters
    params["rag_params"]["method"] = st.selectbox(label="Search method", options=SEARCH_METHODS, index=0)

    if collections:

        @st.dialog(title="Select collections")
        def add_collection(collections: list) -> None:
            selected_collections = st.session_state.selected_collections
            col1, col2 = st.columns(spec=2)

            for collection in collections:
                if st.checkbox(
                    label=f"{collection["name"]} ({collection["id"]})",
                    value=False if collection["id"] not in st.session_state.selected_collections else True,
                ):
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
    else:  # Ensure default values if no collections
        params["rag_params"]["collections"] = []
        # Default k, consistent with number_input default if collections were present
        params["rag_params"]["k"] = 5

    if st.session_state.selected_collections:  # or params["rag_params"]["collections"]
        rag = st.toggle(label="Activated RAG", value=True, disabled=not bool(params["rag_params"]["collections"]))
    else:
        rag = st.toggle(label="Activated RAG", value=False, disabled=True, help="You need to select at least one collection to activate RAG.")

# Main
with st.chat_message(name="assistant"):
    st.markdown(
        body="""Bonjour je suis Albert, et je peux vous aider si vous avez des questions administratives !

Je peux me connecter à vos bases de connaissances, pour ça sélectionnez les collections voulues dans le menu de gauche. Si vous ne souhaitez pas utiliser de collection, désactivez le RAG en décochant la fonction "Activated RAG".
                
Comment puis-je vous aider ?
"""
    )

for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"], avatar=":material/face:" if message["role"] == "user" else None):
        st.markdown(message["content"])
        if st.session_state.sources[i]:
            st.pills(key=str(uuid4()), label="Sources", options=st.session_state.sources[i], label_visibility="hidden")

sources = []
if prompt := st.chat_input(placeholder="Message to Albert"):
    # send message to the model
    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)
    st.session_state.sources.append([])
    with st.chat_message(name="user", avatar=":material/face:"):
        st.markdown(body=prompt)

    with st.chat_message(name="assistant"):
        try:
            stream, sources = generate_stream(
                messages=st.session_state.messages,
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
                formatted_source = source[:15] + "..." if len(source) > 15 else source
                if source.lower().startswith("http"):
                    formatted_sources.append(f":material/globe: [{formatted_source}]({source})")
                else:
                    formatted_sources.append(f":material/import_contacts: {formatted_source}")
            st.pills(label="Sources", options=formatted_sources, label_visibility="hidden")

    assistant_message = {"role": "assistant", "content": response}
    st.session_state.messages.append(assistant_message)
    st.session_state.sources.append(formatted_sources)

with st._bottom:
    st.caption(
        body='<p style="text-align: center;"><i>I can make mistakes, please always verify my sources and answers.</i></p>',
        unsafe_allow_html=True,
    )
