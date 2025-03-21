import time

import requests
from sqlalchemy import select, update
import streamlit as st

from ui.backend.login import get_hashed_password
from ui.backend.settings import settings
from ui.sql.models import User as UserTable
from ui.sql.session import get_session
from ui.utils.common import check_password, get_tokens


def change_password(current_password: str, new_password: str, confirm_password: str):
    session = get_session()
    current_password = session.execute(select(UserTable.password).where(UserTable.name == st.session_state["user"].name)).scalar_one()

    if not check_password(current_password):
        st.toast("Wrong current password", icon="❌")
        return

    if new_password != confirm_password:
        st.toast("New password and confirm password do not match", icon="❌")
        return

    if new_password == current_password:
        st.toast("New password cannot be the same as the current password", icon="❌")
        return

    if not check_password(new_password):
        return

    session.execute(update(UserTable).where(UserTable.name == st.session_state["user"].name).values(password=get_hashed_password(new_password)))
    session.commit()

    st.toast("Password updated", icon="✅")
    time.sleep(0.5)
    st.session_state["login_status"] = False
    st.rerun()


def create_token(token_id: str, expires_at: int):
    response = requests.post(
        url=f"{settings.api_url}/tokens",
        json={"user": st.session_state["user"]["id"], "token": token_id, "expires_at": expires_at},
        headers={"Authorization": f"Bearer {settings.api_key}"},
    )
    if response.status_code == 201:

        @st.dialog(title="Token", width="large")
        def display_token():
            st.warning("**⚠️ Copy the token to your clipboard, it will not be displayed again.**")
            st.code(response.json()["id"], language="text")

        st.toast("Create succeed", icon="✅")
        display_token()
    else:
        st.toast(response.json()["detail"], icon="❌")


def delete_token(token_id: str):
    response = requests.delete(
        url=f"{settings.api_url}/tokens/{st.session_state["user"]["id"]}/{token_id}",
        headers={"Authorization": f"Bearer {settings.api_key}"},
    )
    if response.status_code == 204:
        st.toast("Delete succeed", icon="✅")
        time.sleep(0.5)
        get_tokens.clear()
        st.rerun()
    else:
        st.toast(response.json()["detail"], icon="❌")
