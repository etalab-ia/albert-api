import streamlit as st

from utils.common import settings

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

st.logo(
    image="https://upload.wikimedia.org/wikipedia/fr/thumb/5/50/Bloc_Marianne.svg/1200px-Bloc_Marianne.svg.png",
    link=settings.base_url.replace("/v1", "/playground"),
    size="large",
)

pg = st.navigation(
    pages=[
        st.Page(page="pages/chat.py", title="Chat", icon=":material/chat:"),
        st.Page(page="pages/documents.py", title="Documents", icon=":material/file_copy:"),
        st.Page(page="pages/transcription.py", title="Transcription", icon=":material/graphic_eq:"),
    ]
)
pg.run()
