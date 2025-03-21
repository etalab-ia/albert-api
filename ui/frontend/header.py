import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from ui.backend.login import login
from ui.sql.session import get_session


def header():
    def authenticate():
        session = next(get_session())

        @st.dialog(title="Login")
        def login_form():
            with st.form(key="login"):
                user_name = st.text_input(label="Email", type="default", key="user_id")
                user_password = st.text_input(label="Password", type="password", key="password")
                submit = st.form_submit_button(label="Submit")
                if submit:
                    login(user_name, user_password, session)

        if st.session_state.get("login_status") is None:
            login_form()

    with stylable_container(
        key="Header",
        css_styles="""
        button{
            float: right;
            
        }
    """,
    ):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Albert playground")

        # Authentication
        authenticate()
        if st.session_state.get("login_status") is None:
            st.stop()

        with col2:
            logout = st.button("Logout")
        if logout:
            st.session_state.pop("login_status", default=None)
            st.session_state.pop("user", default=None)
            st.session_state.pop("api_key", default=None)
            st.cache_data.clear()
            st.rerun()
        st.markdown("***")
