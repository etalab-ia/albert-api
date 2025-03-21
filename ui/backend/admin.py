from ast import Name
import logging
import time
from typing import Optional

import requests
from sqlalchemy import insert
import streamlit as st

from ui.backend.login import get_hashed_password
from ui.backend.settings import settings
from ui.sql.models import User as UserTable
from ui.sql.session import get_session
from ui.utils.common import check_password, get_roles, get_users


def create_role(role: str, default: bool):
    response = requests.post(
        url=f"{settings.api_url}/roles",
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
        json={"role": role, "default": default},
    )
    if response.status_code == 201:
        st.toast("Role created", icon="✅")
        get_roles.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        logging.debug(response.text)
        st.toast(response.json()["detail"], icon="❌")


def delete_role(role: str):
    response = requests.delete(url=f"{settings.api_url}/roles/{role}", headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"})
    if response.status_code == 204:
        st.toast("Role deleted", icon="✅")
        get_roles.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast(response.json()["detail"], icon="❌")


def update_role(
    role_id: int, name: Optional[str] = None, default: Optional[bool] = None, permissions: Optional[list] = None, limits: Optional[list] = None
):
    response = requests.patch(
        url=f"{settings.api_url}/roles/{role_id}",
        json={"name": Name(), "default": default, "permissions": permissions, "limits": limits},
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )
    if response.status_code == 200:
        st.toast("Role updated", icon="✅")
        get_roles.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        logging.debug(response.text)
        st.toast(response.json()["detail"], icon="❌")


def create_user(name: str, password: str, role_id: int, expires_at: Optional[int] = None):
    if not check_password(password):
        return

    response = requests.post(
        url=f"{settings.api_url}/users",
        json={"user": name, "role": role_id, "expires_at": expires_at},
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code == 201:
        session = get_session()
        session.execute(
            insert(UserTable).values(
                name=name,
                user_id=response.json()["id"],
                password=get_hashed_password(password),
                role=role_id,
                expires_at=expires_at,
            )
        )
        session.commit()
        st.toast("User created", icon="✅")
        get_users.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast(response.json()["detail"], icon="❌")


def delete_user(user_id: int):
    response = requests.delete(url=f"{settings.api_url}/users/{user_id}", headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"})
    if response.status_code == 204:
        st.toast("User deleted", icon="✅")
        get_users.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast(response.json()["detail"], icon="❌")


def update_user(
    user_id: str, name: Optional[str] = None, password: Optional[str] = None, role: Optional[str] = None, expires_at: Optional[int] = None
):
    if password and not check_password(password):
        return

    response = requests.patch(
        url=f"{settings.api_url}/users/{user_id}",
        json={"name": name, "role": role, "expires_at": expires_at},
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )
    if response.status_code == 200:
        st.toast("User updated", icon="✅")
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast(response.json()["detail"], icon="❌")
