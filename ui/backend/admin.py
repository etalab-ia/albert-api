import time
from typing import Optional

import requests
from sqlalchemy import delete, insert, select, update
import streamlit as st

from ui.backend.common import check_password
from ui.backend.login import get_hashed_password
from ui.backend.sql.models import User as UserTable
from ui.backend.sql.session import get_session
from ui.settings import settings


def create_role(name: str, default: bool, permissions: list, limits: list):
    response = requests.post(
        url=f"{settings.playground.api_url}/roles",
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
        json={"name": name, "default": default, "permissions": permissions, "limits": limits},
    )
    if response.status_code != 201:
        st.toast(response.json()["detail"], icon="❌")
        return

    st.toast("Role created", icon="✅")
    time.sleep(0.5)
    st.rerun()


def delete_role(role: int):
    response = requests.delete(
        url=f"{settings.playground.api_url}/roles/{role}", headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"}
    )
    if response.status_code != 204:
        st.toast(response.json()["detail"], icon="❌")
        return

    st.toast("Role deleted", icon="✅")
    time.sleep(0.5)
    st.rerun()


def update_role(
    role: int, name: Optional[str] = None, default: Optional[bool] = None, permissions: Optional[list] = None, limits: Optional[list] = None
):
    response = requests.patch(
        url=f"{settings.playground.api_url}/roles/{role}",
        json={"name": name, "default": default, "permissions": permissions, "limits": limits},
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )
    if response.status_code != 204:
        st.toast(response.json()["detail"], icon="❌")
        return

    st.toast("Role updated", icon="✅")
    time.sleep(0.5)
    st.rerun()


def create_user(name: str, password: str, role: int, expires_at: Optional[int] = None):
    name = name.strip()
    password = password.strip()

    if not check_password(password):
        return

    response = requests.post(
        url=f"{settings.playground.api_url}/users",
        json={"name": name, "role": role, "expires_at": expires_at},
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 201:
        st.toast(response.json()["detail"], icon="❌")
        return

    user_id = response.json()["id"]

    # create token
    response = requests.post(
        url=f"{settings.playground.api_url}/tokens",
        json={"user": user_id, "name": "playground"},
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 201:
        st.toast(response.json()["detail"], icon="❌")
        return

    api_key = response.json()["token"]
    api_key_id = response.json()["id"]

    session = next(get_session())
    session.execute(
        insert(UserTable).values(
            name=name,
            password=get_hashed_password(password=password),
            api_user_id=user_id,
            api_role_id=role,
            api_key_id=api_key_id,
            api_key=api_key,
        )
    )
    session.commit()

    st.toast("User created", icon="✅")
    time.sleep(0.5)
    st.rerun()


def delete_user(user: int):
    response = requests.delete(
        url=f"{settings.playground.api_url}/users/{user}", headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"}
    )
    if response.status_code != 204:
        st.toast(response.json()["detail"], icon="❌")
        return

    session = next(get_session())
    session.execute(delete(UserTable).where(UserTable.api_user_id == user))
    session.commit()
    st.toast("User deleted", icon="✅")
    time.sleep(0.5)
    st.rerun()


def update_user(user: int, name: Optional[str] = None, password: Optional[str] = None, role: Optional[int] = None, expires_at: Optional[int] = None):
    name = name.strip() if name else None
    password = password.strip() if password else None

    if password and not check_password(password):
        return

    response = requests.patch(
        url=f"{settings.playground.api_url}/users/{user}",
        json={"name": name, "role": role, "expires_at": expires_at},
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )
    if response.status_code != 204:
        st.toast(response.json()["detail"], icon="❌")
        return

    session = next(get_session())
    db_user = session.execute(select(UserTable).where(UserTable.api_user_id == user)).scalar_one()

    name = name or db_user.name
    password = get_hashed_password(password) if password else db_user.password
    role = role or db_user.api_role_id

    session.execute(update(UserTable).values(name=name, password=password, api_role_id=role).where(UserTable.api_user_id == user))
    session.commit()

    st.toast("User updated", icon="✅")
    time.sleep(0.5)
    st.rerun()


def refresh_playground_api_key(user: int):
    # create token
    response = requests.post(
        url=f"{settings.playground.api_url}/tokens",
        json={"user": user, "name": "playground"},
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 201:
        st.toast(response.json()["detail"], icon="❌")
        return

    api_key = response.json()["token"]
    api_key_id = response.json()["id"]

    session = next(get_session())
    session.execute(
        update(UserTable)
        .values(
            api_key=api_key,
            api_key_id=api_key_id,
        )
        .where(UserTable.api_user_id == user)
    )
    session.commit()

    st.toast("Playground API key refreshed", icon="✅")
    time.sleep(0.5)
    st.rerun()
