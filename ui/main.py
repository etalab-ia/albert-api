import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from ui.settings import settings

st.set_page_config(
    page_title="Albert playground",
    page_icon="https://www.systeme-de-design.gouv.fr/uploads/apple_touch_icon_8ffa1fa80c.png",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "mailto:etalab@modernisation.gouv.fr",
        "Report a bug": "https://github.com/etalab-ia/albert-api/issues",
        "About": "https://github.com/etalab-ia/albert-api",
    },
)

st.logo(image=settings.playground.logo, link=settings.playground.home_url, size="large")

pg = st.navigation(
    pages=[
        st.Page(page="frontend/account.py", title="My account", icon=":material/account_circle:"),
        st.Page(page="frontend/chat.py", title="Chat", icon=":material/chat:"),
        st.Page(page="frontend/documents.py", title="Documents", icon=":material/file_copy:"),
        st.Page(page="frontend/summarize.py", title="Summarize", icon=":material/contract_edit:"),
        st.Page(page="frontend/transcription.py", title="Transcription", icon=":material/graphic_eq:"),
        st.Page(page="frontend/admin.py", title="Admin", icon=":material/admin_panel_settings:"),
    ]
)
pg.run()
