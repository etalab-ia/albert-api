import logging
import traceback

from openai import OpenAI
import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from config import BASE_URL, SUPPORTED_LANGUAGES
from utils import get_models, set_config, authenticate

# Config
set_config()
API_KEY = authenticate()

# Data
try:
    _, _, audio_models = get_models(api_key=API_KEY)
except Exception:
    st.error("Error to fetch user data.")
    logging.error(traceback.format_exc())
    st.stop()

openai_client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# Sidebar
with st.sidebar:
    params = {}

    st.title("Audio parameters")
    params["model"] = st.selectbox("Audio model", audio_models)
    params["temperature"] = st.slider("Temperature", value=0.2, min_value=0.0, max_value=1.0, step=0.1)
    params["language"] = st.selectbox("Language", SUPPORTED_LANGUAGES, index=SUPPORTED_LANGUAGES.index("french"))

# Main
col1, col2 = st.columns(2)
with col1:
    file = st.file_uploader("Upload an audio file", type=["mp3", "wav", "m4a"])
with col2:
    record = st.audio_input(label="Record a voice message")

if file and record:
    st.error("Please upload only one file at a time.")
    st.stop()

audio = record or file
result = None

with stylable_container(
    key="Transcribe",
    css_styles="""
    button{
        float: right;
    }
    """,
):
    submit = st.button("Transcribe")

if submit and audio:
    with st.spinner("Transcribing audio..."):
        try:
            response = openai_client.audio.transcriptions.create(
                file=audio,
                model=params["model"],
                temperature=params["temperature"],
            )
            result = response.text
        except Exception:
            st.error("Error transcribing audio.")
            logging.error(traceback.format_exc())

if result:
    st.caption("Result")
    with stylable_container(
        "codeblock",
        """
    code {
        white-space: pre-wrap !important;
    }
    """,
    ):
        st.code(result, language="markdown")
