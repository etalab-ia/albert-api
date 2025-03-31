import logging
import traceback

from openai import OpenAI
import streamlit as st

from ui.backend.common import get_models, settings
from ui.frontend.header import header
from ui.variables import MODEL_TYPE_AUDIO, TRANSCRIPTION_SUPPORTED_LANGUAGES

header()

# Data
try:
    models = get_models(type=MODEL_TYPE_AUDIO)
except Exception:
    st.error(body="Error to fetch user data.")
    logging.error(traceback.format_exc())
    st.stop()

openai_client = OpenAI(base_url=f"{settings.playground.api_url}/v1", api_key=st.session_state["user"].api_key)

# Sidebar
with st.sidebar:
    params = {}
    st.subheader(body="Audio parameters")
    params["model"] = st.selectbox(label="Audio model", options=models)
    params["temperature"] = st.slider(label="Temperature", value=0.2, min_value=0.0, max_value=1.0, step=0.1)
    params["language"] = st.selectbox(
        label="Language", options=TRANSCRIPTION_SUPPORTED_LANGUAGES, index=TRANSCRIPTION_SUPPORTED_LANGUAGES.index("french")
    )

# Main
col1, col2 = st.columns(spec=2)
file = st.file_uploader(label="Upload an audio file", type=["mp3", "wav", "m4a"])
record = st.audio_input(label="Record a voice message")

if file and record:
    st.error(body="Please upload only one file at a time.")
    st.stop()

audio = record or file
result = None
_, center, _ = st.columns(spec=3)
with center:
    submit = st.button(label="**Transcribe**", use_container_width=True)

if submit and audio:
    with st.spinner(text="Transcribing audio..."):
        try:
            response = openai_client.audio.transcriptions.create(
                file=audio,
                model=params["model"],
                temperature=params["temperature"],
            )
            result = response.text
        except Exception:
            st.error(body="Error transcribing audio.")
            logging.error(traceback.format_exc())

if result:
    st.caption(body="Result")
    st.code(body=result, language="markdown", wrap_lines=True)
