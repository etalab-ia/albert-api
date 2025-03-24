import logging
import time
from typing import Optional

import requests
from sqlalchemy import insert, select, update, delete
import streamlit as st

from ui.backend.login import get_hashed_password
from ui.backend.settings import settings
from ui.sql.models import User as UserTable
from ui.sql.session import get_session
from ui.utils.common import check_password, get_roles, get_users


def create_role(name: str, default: bool, permissions: list, limits: list):
    response = requests.post(
        url=f"{settings.api_url}/roles",
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
        json={"name": name, "default": default, "permissions": permissions, "limits": limits},
    )
    if response.status_code == 201:
        st.toast("Role created", icon="✅")
        get_roles.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        logging.debug(response.text)
        st.toast(response.json()["detail"], icon="❌")


def delete_role(role: int):
    response = requests.delete(url=f"{settings.api_url}/roles/{role}", headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"})
    if response.status_code == 204:
        st.toast("Role deleted", icon="✅")
        get_roles.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast(response.json()["detail"], icon="❌")


def update_role(
    role: int, name: Optional[str] = None, default: Optional[bool] = None, permissions: Optional[list] = None, limits: Optional[list] = None
):
    response = requests.patch(
        url=f"{settings.api_url}/roles/{role}",
        json={"name": name, "default": default, "permissions": permissions, "limits": limits},
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )
    if response.status_code == 204:
        st.toast("Role updated", icon="✅")
        get_roles.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        logging.debug(response.text)
        st.toast(response.json()["detail"], icon="❌")


def create_user(name: str, password: str, role: int, expires_at: Optional[int] = None):
    if not check_password(password):
        return

    response = requests.post(
        url=f"{settings.api_url}/users",
        json={"name": name, "role": role, "expires_at": expires_at},
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 201:
        st.toast(response.json()["detail"], icon="❌")

    user_id = response.json()["id"]

    # create token
    response = requests.post(
        url=f"{settings.api_url}/tokens",
        json={"user": user_id, "token": "playground"},
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 201:
        st.toast(response.json()["detail"], icon="❌")

    api_key = response.json()["token"]

    session = next(get_session())
    session.execute(
        insert(UserTable).values(
            name=name,
            password=get_hashed_password(password=password),
            api_user_id=user_id,
            api_role_id=role,
            api_key=api_key,
            expires_at=expires_at,
        )
    )
    session.commit()

    st.toast("User created", icon="✅")
    get_users.clear()
    time.sleep(0.5)
    st.rerun()


def delete_user(user: int):
    response = requests.delete(url=f"{settings.api_url}/users/{user}", headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"})
    if response.status_code != 204:
        st.toast(response.json()["detail"], icon="❌")
        # Also delete the user from the UI database
        session = next(get_session())
        session.execute(delete(UserTable).where(UserTable.api_user_id == user))
        session.commit()
        st.toast("User deleted", icon="✅")
        get_users.clear()
        time.sleep(0.5)
        st.rerun()


def update_user(user: int, name: Optional[str] = None, password: Optional[str] = None, role: Optional[int] = None, expires_at: Optional[int] = None):
    if password and not check_password(password):
        return

    response = requests.patch(
        url=f"{settings.api_url}/users/{user}",
        json={"name": name, "role": role, "expires_at": expires_at},
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )
    if response.status_code != 204:
        st.toast(response.json()["detail"], icon="❌")

    session = next(get_session())
    db_user = session.execute(select(UserTable).where(UserTable.api_user_id == user)).scalar_one()

    name = name or db_user.name
    password = get_hashed_password(password) if password else db_user.password
    role = role or db_user.api_role_id
    expires_at = expires_at or db_user.expires_at

    session.execute(
        update(UserTable)
        .values(
            name=name,
            password=password,
            api_role_id=role,
            expires_at=expires_at,
        )
        .where(UserTable.api_user_id == user)
    )
    session.commit()

    st.toast("User updated", icon="✅")
    get_users.clear()
    time.sleep(0.5)
    st.rerun()
