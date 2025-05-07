from typing import Any, Literal

import pandas as pd
import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from ui.backend.common import get_collections, get_documents, get_roles, get_users


def ressources_selector(ressource: Literal["collection", "role", "user", "document"], filter: Any = None, per_page: int = 30):
    key = f"{ressource}-offset"
    if ressource == "role":
        ressources = get_roles(offset=st.session_state.get(key, 0), limit=per_page)
        new_ressource = {"name": None, "permissions": [], "limits": [], "id": None}

        data = pd.DataFrame(
            data=[
                {
                    "ID": role["id"],
                    "Name": role["name"],
                    "Users": role["users"],
                    "Created at": pd.to_datetime(role["created_at"], unit="s"),
                    "Updated at": pd.to_datetime(role["updated_at"], unit="s"),
                }
                for role in ressources
            ],
        )
        column_config = {
            "ID": st.column_config.TextColumn(label="ID", width="small"),
            "Name": st.column_config.ListColumn(label="Name", width="large"),
            "Created at": st.column_config.DatetimeColumn(format="D MMM YYYY", disabled=True, width="small"),
            "Updated at": st.column_config.DatetimeColumn(format="D MMM YYYY", disabled=True, width="small"),
        }
        new_ressource = {"name": None, "permissions": [], "limits": [], "id": None}

    elif ressource == "user":
        ressources = get_users(offset=st.session_state.get(key, 0), limit=per_page, role=filter)
        new_ressource = {"name": None, "access_ui": False, "expires_at": None, "id": None, "role": None}

        data = pd.DataFrame(
            data=[
                {
                    "ID": user["id"],
                    "Name": user["name"],
                    "Access UI": user["access_ui"],
                    "Expires at": pd.to_datetime(user["expires_at"], unit="s") if user["expires_at"] else None,
                    "Created at": pd.to_datetime(user["created_at"], unit="s"),
                    "Updated at": pd.to_datetime(user["updated_at"], unit="s"),
                }
                for user in ressources
            ],
        )
        column_config = {
            "ID": st.column_config.TextColumn(label="ID", width="small"),
            "Name": st.column_config.ListColumn(label="Name", width="large"),
            "Access UI": st.column_config.CheckboxColumn(label="Access UI", help="If true, the user has created by the admin UI.", width="small"),
            "Expires at": st.column_config.DatetimeColumn(format="D MMM YYYY", width="small"),
            "Created at": st.column_config.DatetimeColumn(format="D MMM YYYY", width="small"),
            "Updated at": st.column_config.DatetimeColumn(format="D MMM YYYY", width="small"),
        }
    elif ressource == "document":
        ressources = get_documents(offset=st.session_state.get(key, 0), limit=per_page, collection_id=filter)
        new_ressource = {}

        data = pd.DataFrame(
            data=[
                {
                    "ID": document["id"],
                    "Name": document["name"],
                    "Chunks": document["chunks"],
                    "Created at": pd.to_datetime(document["created_at"], unit="s"),
                }
                for document in ressources
            ]
        )
        column_config = {
            "ID": st.column_config.TextColumn(label="ID", width="small"),
            "Name": st.column_config.TextColumn(label="Name", width="medium"),
            "Chunks": st.column_config.TextColumn(label="Chunks", width="small"),
            "Created at": st.column_config.DatetimeColumn(format="D MMM YYYY"),
        }

    else:  # collection
        ressources = get_collections(offset=st.session_state.get(key, 0), limit=per_page)
        new_ressource = {"name": None, "description": None, "id": None}

        data = pd.DataFrame(
            data=[
                {
                    "ID": collection["id"],
                    "Name": collection["name"],
                    "Visibility": collection["visibility"],
                    "Owner": collection["owner"],
                    "Documents": collection["documents"],
                    "Description": collection["description"],
                    "Updated at": pd.to_datetime(collection["updated_at"], unit="s"),
                    "Created at": pd.to_datetime(collection["created_at"], unit="s"),
                }
                for collection in ressources
            ],
        )
        column_config = {
            "ID": st.column_config.TextColumn(label="ID", width="small"),
            "Name": st.column_config.TextColumn(label="Name", width="medium"),
            "Visibility": st.column_config.ListColumn(label="Visibility", width="small"),
            "Owner": st.column_config.ListColumn(label="Owner", width="small"),
            "Documents": st.column_config.TextColumn(label="Documents", width="small"),
            "Description": st.column_config.TextColumn(label="Description", width="small"),
            "Updated at": st.column_config.DatetimeColumn(format="D MMM YYYY"),
            "Created at": st.column_config.DatetimeColumn(format="D MMM YYYY"),
        }

    st.dataframe(data=data, hide_index=True, use_container_width=True, column_config=column_config, height=28 * len(ressources) + 37, row_height=28)
    pagination(key, data=ressources, per_page=per_page)

    selected_ressource_name = st.selectbox(
        label=f"Selected {ressource}",
        options=[f"{ressource["name"]} ({ressource["id"]})" for ressource in ressources],
        disabled=st.session_state.get(f"new_{ressource}", False),
    )

    # reset pagination if filter is changed
    if filter and st.session_state.get(f"filter_{ressource}", None) != filter:
        st.session_state[key] = 0
        st.session_state[f"filter_{ressource}"] = filter
        st.rerun()

    selected_ressource = [ressource for ressource in ressources if f"{ressource['name']} ({ressource['id']})" == selected_ressource_name][0] if ressources else {}  # fmt: off
    selected_ressource = new_ressource if st.session_state.get(f"new_{ressource}", False) else selected_ressource
    st.session_state[f"selected_{ressource}"] = selected_ressource

    return ressources, selected_ressource


def pagination(key: str, data: list, per_page: int = 10):
    _, left, center, right, _ = st.columns(spec=[8, 1.5, 1.5, 1.5, 8])
    with left:
        if st.button(
            label="**:material/keyboard_double_arrow_left:**",
            key=f"pagination-{key}-previous",
            disabled=st.session_state.get(key, 0) == 0,
            use_container_width=True,
        ):
            st.session_state[key] = max(0, st.session_state.get(key, 0) - per_page)
            st.rerun()

    with center:
        st.button(label=str(round(st.session_state.get(key, 0) / per_page)), key=f"pagination-{key}", use_container_width=True)

    with right:
        with stylable_container(key="Header", css_styles="button{float: right;}"):
            if st.button(
                label="**:material/keyboard_double_arrow_right:**",
                key=f"pagination-{key}-next",
                disabled=len(data) < per_page,
                use_container_width=True,
            ):
                st.session_state[key] = st.session_state.get(key, 0) + per_page
                st.rerun()
