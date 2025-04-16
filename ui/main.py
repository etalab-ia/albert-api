import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from ui.settings import settings

st.set_page_config(
    page_title="Albert playground",
    page_icon=settings.playground.page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": settings.playground.menu_items.get_help,
        "Report a bug": settings.playground.menu_items.report_a_bug,
        "About": settings.playground.menu_items.about,
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
