import logging
import time
from typing import Optional

import requests
import streamlit as st

from utils.common import check_password, get_roles, get_users, settings


def create_role(role: str, default: bool):
    response = requests.post(
        url=f"{settings.api_url}/roles",
        headers={"Authorization": f"Bearer {settings.api_key}"},
        json={"role": role, "default": default},
    )
    if response.status_code == 201:
        st.toast("Role created", icon="✅")
        get_roles.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        logging.debug(response.text)
        st.toast("Role creation failed", icon="❌")


def delete_role(role: str):
    response = requests.delete(url=f"{settings.api_url}/roles/{role}", headers={"Authorization": f"Bearer {settings.api_key}"})
    if response.status_code == 204:
        st.toast("Role deleted", icon="✅")
        get_roles.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast(response.json()["detail"], icon="❌")


def update_role(
    role_id: str, role: Optional[str] = None, default: Optional[bool] = None, permissions: Optional[list] = None, limits: Optional[list] = None
):
    response = requests.patch(
        url=f"{settings.api_url}/roles/{role_id}",
        json={"role": role, "default": default, "permissions": permissions, "limits": limits},
        headers={"Authorization": f"Bearer {settings.api_key}"},
    )
    if response.status_code == 200:
        st.toast("Role updated", icon="✅")
        get_roles.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        logging.debug(response.text)
        st.toast(response.json()["detail"], icon="❌")


def create_user(user: str, password: str, role: str, expires_at: Optional[int] = None):
    if not check_password(password):
        return

    response = requests.post(
        url=f"{settings.api_url}/users",
        json={"user": user, "password": password, "role": role, "expires_at": expires_at},
        headers={"Authorization": f"Bearer {settings.api_key}"},
    )
    if response.status_code == 201:
        st.toast("User created", icon="✅")
        get_users.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast(response.json()["detail"], icon="❌")


def delete_user(user: str):
    response = requests.delete(url=f"{settings.api_url}/users/{user}", headers={"Authorization": f"Bearer {settings.api_key}"})
    if response.status_code == 204:
        st.toast("User deleted", icon="✅")
        get_users.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast(response.json()["detail"], icon="❌")


def update_user(
    user_id: str, user: Optional[str] = None, password: Optional[str] = None, role: Optional[str] = None, expires_at: Optional[int] = None
):
    if password and not check_password(password):
        return

    response = requests.patch(
        url=f"{settings.api_url}/users/{user_id}",
        json={"user": user, "password": password, "role": role, "expires_at": expires_at},
        headers={"Authorization": f"Bearer {settings.api_key}"},
    )
    if response.status_code == 200:
        st.toast("User updated", icon="✅")
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast(response.json()["detail"], icon="❌")
