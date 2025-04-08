import bcrypt
from pydantic import BaseModel
import requests
from sqlalchemy import select
from sqlalchemy.orm import Session
import streamlit as st

from ui.settings import settings
from ui.backend.sql.models import User as UserTable
from ui.variables import ADMIN_PERMISSIONS


class User(BaseModel):
    id: int
    name: str
    api_key: str
    role: dict
    user: dict


def get_hashed_password(password: str) -> str:
    return bcrypt.hashpw(password=password.encode(encoding="utf-8"), salt=bcrypt.gensalt()).decode(encoding="utf-8")


def check_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password=password.encode(encoding="utf-8"), hashed_password=hashed_password.encode(encoding="utf-8"))


def login(user_name: str, user_password: str, session: Session) -> dict:
    # master login flow
    if user_name == settings.auth.master_username:
        response = requests.get(url=f"{settings.playground.api_url}/users/me", headers={"Authorization": f"Bearer {user_password}"})
        if response.status_code != 404:  # only master get 404 on /users/me
            st.error(response.json()["detail"])
            st.stop()

        response = requests.get(url=f"{settings.playground.api_url}/v1/models", headers={"Authorization": f"Bearer {user_password}"})
        if response.status_code != 200:
            st.error(response.json()["detail"])
            st.stop()
        models = response.json()["data"]

        limits = []
        for model in models:
            limits.append({"model": model["id"], "type": "tpm", "value": None})
            limits.append({"model": model["id"], "type": "tpd", "value": None})
            limits.append({"model": model["id"], "type": "rpm", "value": None})
            limits.append({"model": model["id"], "type": "rpd", "value": None})

        role = {"object": "role", "id": 0, "name": "master", "default": False, "permissions": ADMIN_PERMISSIONS, "limits": limits}
        user = User(id=0, name=settings.auth.master_username, api_key=user_password, user={"expires_at": None}, role=role)

        st.session_state["login_status"] = True
        st.session_state["user"] = user
        st.rerun()

    # basic login flow
    db_user = session.execute(select(UserTable).where(UserTable.name == user_name)).scalar_one_or_none()
    if not db_user:
        st.error("Invalid username or password")
        st.stop()

    if not check_password(password=user_password, hashed_password=db_user.password):
        st.error("Invalid username or password")
        st.stop()

    response = requests.get(url=f"{settings.playground.api_url}/users/me", headers={"Authorization": f"Bearer {db_user.api_key}"})
    if response.status_code != 200:
        st.error(response.json()["detail"])
        st.stop()
    user = response.json()

    response = requests.get(url=f"{settings.playground.api_url}/roles/me", headers={"Authorization": f"Bearer {db_user.api_key}"})
    if response.status_code != 200:
        st.error(response.json()["detail"])
        st.stop()
    role = response.json()

    user = User(id=db_user.id, name=db_user.name, api_key=db_user.api_key, user=user, role=role)

    st.session_state["login_status"] = True
    st.session_state["user"] = user
    st.rerun()
