import time

import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from ui.backend.login import login
from ui.backend.sql.session import get_session
from .css import css_proconnect


def header():
    def authenticate():
        session = next(get_session())

        @st.dialog(title="Login")
        def login_form():
            with st.form(key="login"):
                user_name = st.text_input(label="Email", type="default", key="user_id", icon=":material/email:")
                user_password = st.text_input(label="Password", type="password", key="password", icon=":material/lock:")

                # strip input
                user_name = user_name.strip()
                user_password = user_password.strip()

                submit = st.form_submit_button(label="Submit")
                if submit:
                    login(user_name, user_password, session)

                with stylable_container(key="ProConnect", css_styles=css_proconnect):
                    # ProConnect Button
                    st.markdown(
                        """
                      <div>
                        <form action="#" method="post">
                          <button class="proconnect-button">
                            <span class="proconnect-sr-only">S'identifier avec ProConnect</span>
                          </button>
                        </form>
                        <p>
                          <a
                            href="https://www.proconnect.gouv.fr/"
                            target="_blank"
                            rel="noopener noreferrer"
                            title="Qu’est-ce que ProConnect ? - nouvelle fenêtre"
                          >
                            Qu’est-ce que ProConnect ?
                          </a>
                        </p>
                      </div>
                      """,
                        unsafe_allow_html=True,
                    )

        if st.session_state.get("login_status") is None:
            login_form()

    with stylable_container(key="Header", css_styles="button{float: right;}"):
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

        if st.session_state.get("user") and st.session_state["user"].role["name"] == "master":
            st.warning("You are logged in as the master user. This is not recommended for production use, please use a regular user instead.")
        if st.session_state.get("user") and st.session_state["user"].user["expires_at"] and st.session_state["user"].user["expires_at"] < int(time.time()):  # fmt: off
            st.warning("**Your account has expired. Please contact support to renew your account.**")
        st.markdown("***")
