import logging
import traceback

from openai import OpenAI
import streamlit as st

from config import BASE_URL, SUPPORTED_LANGUAGES
from utils import get_models, header

API_KEY = header()

# Data
try:
    _, _, audio_models, _ = get_models(api_key=API_KEY)
except Exception:
    st.error("Error to fetch user data.")
    logging.error(traceback.format_exc())
    st.stop()

openai_client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# Sidebar
with st.sidebar:
    params = {}
    st.subheader("Audio parameters")
    params["model"] = st.selectbox(label="Audio model", options=audio_models)
    params["temperature"] = st.slider(label="Temperature", value=0.2, min_value=0.0, max_value=1.0, step=0.1)
    params["language"] = st.selectbox(label="Language", options=SUPPORTED_LANGUAGES, index=SUPPORTED_LANGUAGES.index("french"))

# Main
col1, col2 = st.columns(2)
file = st.file_uploader("Upload an audio file", type=["mp3", "wav", "m4a"])
record = st.audio_input(label="Record a voice message")

if file and record:
    st.error("Please upload only one file at a time.")
    st.stop()

audio = record or file
result = None
_, center, _ = st.columns(spec=3)
with center:
    submit = st.button("**Transcribe**", use_container_width=True)

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
    st.code(result, language="markdown", wrap_lines=True)
