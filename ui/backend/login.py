import secrets
import string

import bcrypt
from pydantic import BaseModel
import requests
from sqlalchemy import insert, select
from sqlalchemy.orm import Session
import streamlit as st

from ui.backend.sql.models import User as UserTable
from ui.configuration import configuration
from ui.variables import ADMIN_PERMISSIONS


class User(BaseModel):
    id: int
    name: str
    api_key_id: int
    api_key: str
    role: dict
    user: dict


def get_hashed_password(password: str) -> str:
    return bcrypt.hashpw(password=password.encode(encoding="utf-8"), salt=bcrypt.gensalt()).decode(encoding="utf-8")


def check_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password=password.encode(encoding="utf-8"), hashed_password=hashed_password.encode(encoding="utf-8"))


def login(user_name: str, user_password: str, session: Session, oauth2=False) -> dict:
    # master login flow
    if user_name == configuration.playground.auth_master_username:
        response = requests.get(url=f"{configuration.playground.api_url}/users/me", headers={"Authorization": f"Bearer {user_password}"})
        if response.status_code != 404:  # only master get 404 on /users/me
            st.error(response.json()["detail"])
            st.stop()

        response = requests.get(url=f"{configuration.playground.api_url}/v1/models", headers={"Authorization": f"Bearer {user_password}"})
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
        user = User(
            id=0,
            name=configuration.playground.auth_master_username,
            api_key=user_password,
            api_key_id=0,
            user={"expires_at": None, "budget": None},
            role=role,
        )

        st.session_state["login_status"] = True
        st.session_state["user"] = user
        st.rerun()

    # basic login flow
    db_user = session.execute(select(UserTable).where(UserTable.name == user_name)).scalar_one_or_none()
    if not db_user:
        st.error("Invalid username or password")
        st.stop()

    if not oauth2 and not check_password(password=user_password, hashed_password=db_user.password):
        st.error("Invalid username or password")
        st.stop()

    response = requests.get(url=f"{configuration.playground.api_url}/users/me", headers={"Authorization": f"Bearer {db_user.api_key}"})
    if response.status_code != 200:
        st.error(response.json()["detail"])
        st.stop()
    user = response.json()

    response = requests.get(url=f"{configuration.playground.api_url}/roles/me", headers={"Authorization": f"Bearer {db_user.api_key}"})
    if response.status_code != 200:
        st.error(response.json()["detail"])
        st.stop()
    role = response.json()

    user = User(id=db_user.id, name=db_user.name, api_key_id=db_user.api_key_id, api_key=db_user.api_key, user=user, role=role)

    st.session_state["login_status"] = True
    st.session_state["user"] = user
    st.rerun()


def generate_random_password(length: int = 16) -> str:
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def oauth_login(session: Session, api_key: str, api_key_id: str):
    """After OAuth2 login, backend will provide api_key and api_key_id in URL parameters and we use it to process the login"""
    response = requests.get(url=f"{settings.playground.api_url}/users/me", headers={"Authorization": f"Bearer {api_key}"})
    if response.status_code != 200:
        st.error(response.json()["detail"])
        st.stop()
    user = response.json()

    response = requests.get(url=f"{settings.playground.api_url}/roles/me", headers={"Authorization": f"Bearer {api_key}"})
    if response.status_code != 200:
        st.error(response.json()["detail"])
        st.stop()
    role = response.json()
    db_user = session.execute(select(UserTable).where(UserTable.name == user["name"])).scalar_one_or_none()
    if not db_user:
        session.execute(
            insert(UserTable).values(
                name=user["name"],
                password=get_hashed_password(password=generate_random_password()),
                api_user_id=user["id"],
                api_role_id=role["id"],
                api_key_id=api_key_id,
                api_key=api_key,
            )
        )
        session.commit()
    else:
        session.execute(
            UserTable.__table__.update()
            .where(UserTable.id == db_user.id)
            .values(
                api_key=api_key,
                api_key_id=api_key_id,
                api_user_id=user["id"],
                api_role_id=role["id"],
            )
        )
        session.commit()

    # Clear the URL parameters after processing
    st.query_params.clear()
    login(user["name"], None, session, oauth2=True)
