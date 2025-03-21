import bcrypt
from pydantic import BaseModel
import requests
from sqlalchemy import select
from sqlalchemy.orm import Session
import streamlit as st

from ui.backend.settings import settings
from ui.sql.models import User as UserTable


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
    # admin login flow
    if user_name == settings.admin_name and user_password == settings.admin_password:
        response = requests.get(url=f"{settings.api_url}/users/me", headers={"Authorization": f"Bearer {settings.api_key}"})

        if response.status_code != 200:
            st.error(response.json()["detail"])
            st.stop()

        user = response.json()
        response = requests.get(url=f"{settings.api_url}/roles/{user["role"]}", headers={"Authorization": f"Bearer {settings.api_key}"})

        if response.status_code != 200:
            st.error(response.json()["detail"])
            st.stop()

        role = response.json()
        user = User(id=0, name=settings.admin_name, api_key=settings.api_key, user=user, role=role)

        st.session_state["login_status"] = True
        st.session_state["user"] = user
        st.rerun()

    # non-admin login flow
    db_user = session.execute(select(UserTable).where(UserTable.name == user_name)).limit(1).all()
    if not db_user:
        st.error("Invalid username or password")
        st.stop()
    db_user = [row._mapping for row in db_user][0]

    if not check_password(password=user_password, hashed_password=db_user.password):
        st.error("Invalid username or password")
        st.stop()

    response = requests.get(url=f"{settings.api_url}/users/{db_user.api_user_id}", headers={"Authorization": f"Bearer {settings.api_key}"})
    if response.status_code != 200:
        st.error(response.json()["detail"])
        st.stop()
    api_user = response.json()

    response = requests.get(url=f"{settings.api_url}/roles/{db_user.api_role_id}", headers={"Authorization": f"Bearer {settings.api_key}"})
    if response.status_code != 200:
        st.error(response.json()["detail"])
        st.stop()
    role = response.json()

    user = User(id=db_user.id, name=db_user.name, api_key=db_user.api_key, user=api_user, role=role)

    st.session_state["login_status"] = True
    st.session_state["user"] = user
    st.rerun()
