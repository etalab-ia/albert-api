from typing import Literal

import requests
from sqlalchemy import select
import streamlit as st

from ui.backend.sql.models import User as UserTable
from ui.backend.sql.session import get_session
from ui.configuration import configuration
from ui.variables import MODEL_TYPE_AUDIO, MODEL_TYPE_EMBEDDINGS, MODEL_TYPE_IMAGE_TEXT_TO_TEXT, MODEL_TYPE_LANGUAGE, MODEL_TYPE_RERANK


@st.cache_data(show_spinner=False, ttl=configuration.playground.cache_ttl)
def get_models(
    types: list[Literal[MODEL_TYPE_LANGUAGE, MODEL_TYPE_IMAGE_TEXT_TO_TEXT, MODEL_TYPE_EMBEDDINGS, MODEL_TYPE_AUDIO, MODEL_TYPE_RERANK]] = [],
) -> list:
    response = requests.get(
        url=f"{configuration.playground.api_url}/v1/models", headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"}
    )
    if response.status_code != 200:
        st.error(response.json()["detail"])
        return []

    models = response.json()["data"]
    if types == []:
        models = sorted([model["id"] for model in models], key=lambda x: x.lower())
    else:
        models = sorted([model["id"] for model in models if model["type"] in types], key=lambda x: x.lower())

    return models


def get_collections(offset: int = 0, limit: int = 10) -> list:
    response = requests.get(
        url=f"{configuration.playground.api_url}/v1/collections?offset={offset}&limit={limit}",
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 200:
        st.error(response.json()["detail"])
        return []

    data = response.json()["data"]

    return data


def get_documents(collection_id: int, offset: int = 0, limit: int = 10) -> dict:
    response = requests.get(
        url=f"{configuration.playground.api_url}/v1/documents?collection={collection_id}&offset={offset}&limit={limit}",
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 200:
        st.error(response.json()["detail"])
        return []

    data = response.json()["data"]

    return data


def get_tokens(offset: int = 0, limit: int = 10) -> list:
    response = requests.get(
        url=f"{configuration.playground.api_url}/tokens?offset={offset}&limit={limit}",
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 200:
        st.error(response.json()["detail"])
        return []

    return response.json()["data"]


def get_roles(
    offset: int = 0,
    limit: int = 10,
    order_by: Literal["id", "name", "created_at", "updated_at"] = "id",
    order_direction: Literal["asc", "desc"] = "asc",
):
    response = requests.get(
        url=f"{configuration.playground.api_url}/roles?offset={offset}&limit={limit}&order_by={order_by}&order_direction={order_direction}",
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )
    if response.status_code != 200:
        st.error(response.json()["detail"])
        return []

    data = response.json()["data"]

    return data


def get_users(
    role: int,
    offset: int = 0,
    limit: int = 100,
    order_by: Literal["id", "name", "created_at", "updated_at"] = "id",
    order_direction: Literal["asc", "desc"] = "asc",
):
    response = requests.get(
        url=f"{configuration.playground.api_url}/users?offset={offset}&limit={limit}&role={role}&order_by={order_by}&order_direction={order_direction}",
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )
    if response.status_code != 200:
        st.error(response.json()["detail"])
        return []

    data = response.json()["data"]

    session = next(get_session())
    db_data = session.execute(select(UserTable)).scalars().all()

    # Convert SQLAlchemy User objects to dictionaries
    db_data = [user.api_user_id for user in db_data]

    # Filter API data based on database user IDs
    for user in data:
        user["access_ui"] = True if user["id"] in db_data else False

    return data


def get_limits(models: list, role: dict) -> dict:
    limits = {}
    for model in models:
        limits[model] = {"tpm": 0, "tpd": 0, "rpm": 0, "rpd": 0}
        for limit in role["limits"]:
            if limit["model"] == model and limit["type"] == "tpm":
                limits[model]["tpm"] = limit["value"]
            elif limit["model"] == model and limit["type"] == "tpd":
                limits[model]["tpd"] = limit["value"]
            elif limit["model"] == model and limit["type"] == "rpm":
                limits[model]["rpm"] = limit["value"]
            elif limit["model"] == model and limit["type"] == "rpd":
                limits[model]["rpd"] = limit["value"]

    return limits


def check_password(password: str) -> bool:
    if len(password) < 8:
        st.toast("New password must be at least 8 characters long", icon="❌")
        return False
    if not any(char.isupper() for char in password):
        st.toast("New password must contain at least one uppercase letter", icon="❌")
        return False
    if not any(char.islower() for char in password):
        st.toast("New password must contain at least one lowercase letter", icon="❌")
        return False
    if not any(char.isdigit() for char in password):
        st.toast("New password must contain at least one digit", icon="❌")
        return False

    return True


@st.cache_data(show_spinner=False, ttl=configuration.playground.cache_ttl)
def get_usage(
    limit: int = 50,
    page: int = 1,
    order_by: Literal["datetime", "cost", "total_tokens"] = "datetime",
    order_direction: Literal["asc", "desc"] = "desc",
    date_from: int = None,
    date_to: int = None,
) -> dict:
    """Get user usage data from the API."""
    response = requests.get(
        url=f"{configuration.playground.api_url}/v1/usage",
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
        params={
            "limit": limit,
            "page": page,
            "order_by": order_by,
            "order_direction": order_direction,
            **({"date_from": date_from} if date_from is not None else {}),
            **({"date_to": date_to} if date_to is not None else {}),
        },
    )

    if response.status_code != 200:
        st.error(response.json()["detail"])
        return {
            "data": [],
            "total_requests": 0,
            "total_albert_coins": 0.0,
            "total_tokens": 0,
            "total_co2": 0.0,
            "page": 1,
            "limit": limit,
            "total_pages": 0,
            "has_more": False,
        }

    return response.json()
