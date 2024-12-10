import streamlit as st
from ui.backend.common import get_models


def setup_selected_model(model_type, session_key="selected_model"):
    """
    Sets up the selected model using a selectbox in the sidebar.

    Args:
        model_type (str): The type of models to fetch.
        session_key (str): The session state key to store the selected model.
    """
    models = get_models(type=model_type)
    if session_key not in st.session_state:
        st.session_state[session_key] = models[0] if models else None

    st.sidebar.subheader("Model Selection")
    st.session_state[session_key] = st.sidebar.selectbox(
        label="Select a model",
        options=models,
        index=models.index(st.session_state[session_key]) if st.session_state[session_key] in models else 0,
    )
    return st.session_state[session_key]