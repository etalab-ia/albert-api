from openai import OpenAI

from app.utils.settings import settings

open_ai_client = OpenAI(base_url=settings.playground.api_url + "/v1", api_key=st.session_state["user"].api_key)