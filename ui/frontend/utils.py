from typing import Any, Literal

import pandas as pd
import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from ui.backend.common import get_collections, get_documents, get_limits, get_models, get_roles, get_users


def resources_selector(resource: Literal["collection", "role", "user", "document"], resource_filter: Any = None, per_page: int = 30):
    key = f"{resource}-offset"

    if resource == "role":
        col1, col2 = st.columns(2)
        with col1:
            order_by = st.selectbox(label="Order by", options=["id", "name", "created_at", "updated_at"], index=0, key=f"order_by-{resource}")
        with col2:
            order_direction = st.selectbox(label="Order direction", options=["asc", "desc"], index=0, key=f"order_direction-{resource}")

        resources = get_roles(offset=st.session_state.get(key, 0), limit=per_page, order_by=order_by, order_direction=order_direction)
        new_resource = {"name": None, "permissions": [], "limits": [], "id": None}

        data = pd.DataFrame(
            data=[
                {
                    "ID": role["id"],
                    "Name": role["name"],
                    "Users": role["users"],
                    "Created at": pd.to_datetime(role["created_at"], unit="s"),
                    "Updated at": pd.to_datetime(role["updated_at"], unit="s"),
                }
                for role in resources
            ],
        )
        column_config = {
            "ID": st.column_config.TextColumn(label="ID", width="small"),
            "Name": st.column_config.ListColumn(label="Name", width="large"),
            "Created at": st.column_config.DatetimeColumn(format="D MMM YYYY", disabled=True, width="small"),
            "Updated at": st.column_config.DatetimeColumn(format="D MMM YYYY", disabled=True, width="small"),
        }
        new_resource = {"name": None, "permissions": [], "limits": [], "id": None}

    elif resource == "user":
        col1, col2 = st.columns(2)
        with col1:
            order_by = st.selectbox(label="Order by", options=["id", "name", "created_at", "updated_at"], index=0, key=f"order_by-{resource}")
        with col2:
            order_direction = st.selectbox(label="Order direction", options=["asc", "desc"], index=0, key=f"order_direction-{resource}")

        resources = get_users(offset=st.session_state.get(key, 0), limit=per_page, role=resource_filter, order_by=order_by, order_direction=order_direction)
        new_resource = {"name": None, "access_ui": False, "expires_at": None, "id": None, "role": None}

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
                for user in resources
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
    elif resource == "document":
        resources = get_documents(offset=st.session_state.get(key, 0), limit=per_page, collection_id=resource_filter)
        new_resource = {}

        data = pd.DataFrame(
            data=[
                {
                    "ID": document["id"],
                    "Name": document["name"],
                    "Chunks": document["chunks"],
                    "Created at": pd.to_datetime(document["created_at"], unit="s"),
                }
                for document in resources
            ]
        )
        column_config = {
            "ID": st.column_config.TextColumn(label="ID", width="small"),
            "Name": st.column_config.TextColumn(label="Name", width="medium"),
            "Chunks": st.column_config.TextColumn(label="Chunks", width="small"),
            "Created at": st.column_config.DatetimeColumn(format="D MMM YYYY"),
        }

    else:  # collection
        resources = get_collections(offset=st.session_state.get(key, 0), limit=per_page)
        new_resource = {"name": None, "description": None, "id": None}

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
                for collection in resources
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

    st.dataframe(data=data, hide_index=True, use_container_width=True, column_config=column_config, height=28 * len(resources) + 37, row_height=28)
    pagination(key, data=resources, per_page=per_page)

    selected_resource_name = st.selectbox(
        label=f"Selected {resource}",
        options=[f"{resource["name"]} ({resource["id"]})" for resource in resources],
        disabled=st.session_state.get(f"new_{resource}", False) or st.session_state.get(f"update_{resource}", False),
    )

    # reset pagination if filter is changed
    if resource_filter and st.session_state.get(f"filter_{resource}", None) != resource_filter:
        st.session_state[key] = 0
        st.session_state[f"filter_{resource}"] = resource_filter
        st.rerun()

    selected_resource = [resource for resource in resources if f"{resource['name']} ({resource['id']})" == selected_resource_name][0] if resources else {}  # fmt: off
    selected_resource = new_resource if st.session_state.get(f"new_{resource}", False) else selected_resource
    st.session_state[f"selected_{resource}"] = selected_resource

    return resources, selected_resource


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


# Documents - collections
def input_new_collection_name(selected_collection: dict):
    collection_name = st.text_input(
        label="**Collection name**",
        placeholder="Enter collection name",
        value=selected_collection.get("name"),
        icon=":material/folder:",
        disabled=(not st.session_state.get("new_collection", False) and not st.session_state.get("update_collection", False))
        or (st.session_state["no_collections"] and not st.session_state.get("new_collection", False)),
    )

    return collection_name


def input_new_collection_description(selected_collection: dict):
    collection_description = st.text_input(
        label="**Collection description**",
        placeholder="Enter collection description",
        value=selected_collection.get("description"),
        icon=":material/description:",
        disabled=(not st.session_state.get("new_collection", False) and not st.session_state.get("update_collection", False))
        or (st.session_state["no_collections"] and not st.session_state.get("new_collection", False)),
    )

    return collection_description


# Admin - roles
def input_new_role_name(selected_role: dict):
    new_role_name = st.text_input(
        label="Role name",
        placeholder="Enter role name",
        icon=":material/group:",
        value=selected_role.get("name"),
        disabled=(not st.session_state.get("update_role", False) and not st.session_state.get("new_role", False))
        or (st.session_state["no_roles"] and not st.session_state.get("new_role", False)),
    )

    return new_role_name


def input_new_role_permissions(selected_role: dict):
    with st.popover(
        f"#### Permissions of the *{"new" if st.session_state.get("new_role", False) else selected_role.get("name")}* role",
        use_container_width=True,
    ):
        disabled = (not st.session_state.get("update_role", False) and not st.session_state.get("new_role", False)) or (st.session_state["no_roles"] and not st.session_state.get("new_role", False))  # fmt: off
        col1, col2, col3 = st.columns(spec=3)
        new_role_permissions = []
        with col1:
            st.caption("Roles")
            if st.checkbox(
                label="Create role",
                key="create_role_checkbox",
                value="create_role" in selected_role.get("permissions", []),
                disabled=disabled,
            ):
                new_role_permissions.append("create_role")
            if st.checkbox(
                label="Read role",
                key="read_role_checkbox",
                value="read_role" in selected_role.get("permissions", []),
                disabled=disabled,
            ):
                new_role_permissions.append("read_role")
            if st.checkbox(
                label="Delete role",
                key="delete_role_checkbox",
                value="delete_role" in selected_role.get("permissions", []),
                disabled=disabled,
            ):
                new_role_permissions.append("delete_role")
            if st.checkbox(
                label="Update role",
                key="update_role_checkbox",
                value="update_role" in selected_role.get("permissions", []),
                disabled=disabled,
            ):
                new_role_permissions.append("update_role")

        with col2:
            st.caption("Users")
            if st.checkbox(
                label="Create user",
                key="create_user_checkbox",
                value="create_user" in selected_role.get("permissions", []),
                disabled=disabled,
            ):
                new_role_permissions.append("create_user")
            if st.checkbox(
                label="Read user",
                key="read_user_checkbox",
                value="read_user" in selected_role.get("permissions", []),
                disabled=disabled,
            ):
                new_role_permissions.append("read_user")
            if st.checkbox(
                label="Delete user",
                key="delete_user_checkbox",
                value="delete_user" in selected_role.get("permissions", []),
                disabled=disabled,
            ):
                new_role_permissions.append("delete_user")
            if st.checkbox(
                label="Update user",
                key="update_user_checkbox",
                value="update_user" in selected_role.get("permissions", []),
                disabled=disabled,
            ):
                new_role_permissions.append("update_user")

        with col3:
            st.caption("Others")
            if st.checkbox(
                label="Read metric",
                key="read_metric_checkbox",
                value="read_metric" in selected_role.get("permissions", []),
                disabled=disabled,
            ):
                new_role_permissions.append("read_metric")
            create_public_collection = st.checkbox(
                label="Create public collection",
                key="create_public_collection_checkbox",
                value="create_public_collection" in selected_role.get("permissions", []),
                disabled=disabled,
            )
            if create_public_collection:
                new_role_permissions.append("create_public_collection")

    return new_role_permissions


def input_new_role_limits(selected_role: dict):
    with st.popover(
        f"#### Rate limits of the *{"new" if st.session_state.get("new_role", False) else selected_role.get("name")}* role",
        use_container_width=True,
    ):
        disabled = (not st.session_state.get("update_role", False) and not st.session_state.get("new_role", False)) or (st.session_state["no_roles"] and not st.session_state.get("new_role", False))  # fmt: off
        models = get_models() + ["web-search"]
        limits = (
            {model: {"rpm": None, "rpd": None, "tpm": None, "tpd": None} for model in models}
            if not st.session_state.get("new_role", False) and st.session_state["no_roles"]
            else get_limits(models=models, role=selected_role)
        )
        initial_limits = pd.DataFrame(
            data={
                "Request per minute": [limits[model]["rpm"] for model in models],
                "Request per day": [limits[model]["rpd"] for model in models],
                "Tokens per minute": [limits[model]["tpm"] for model in models],
                "Tokens per day": [limits[model]["tpd"] for model in models],
            },
            index=models,
        )

        edited_limits = initial_limits.copy()
        edited_limits = st.data_editor(
            data=edited_limits,
            use_container_width=True,
            disabled=True if disabled else ["_index"],
            column_config={
                "_index": st.column_config.ListColumn(label="", width="medium"),
                "Request per minute": st.column_config.NumberColumn(label="Request per minute", min_value=0, step=1, required=False, width="small"),
                "Request per day": st.column_config.NumberColumn(label="Request per day", min_value=0, step=1, required=False, width="small"),
                "Tokens per minute": st.column_config.NumberColumn(label="Tokens per minute", min_value=0, step=1, required=False, width="small"),
                "Tokens per day": st.column_config.NumberColumn(label="Tokens per day", min_value=0, step=1, required=False, width="small"),
            },
            height=28 * len(models) + 37,
            row_height=28,
        )
        new_role_limits = []
        for model, row in edited_limits.iterrows():
            for rate_type in row.index:
                value = None if pd.isna(row[rate_type]) else int(row[rate_type])
                rate_type = "tpm" if rate_type == "Tokens per minute" else rate_type
                rate_type = "tpd" if rate_type == "Tokens per day" else rate_type
                rate_type = "rpm" if rate_type == "Request per minute" else rate_type
                rate_type = "rpd" if rate_type == "Request per day" else rate_type
                new_role_limits.append({"model": model, "type": rate_type, "value": value})

    return new_role_limits


# Admin - users
def input_new_user_name(selected_user: dict):
    new_user_name = st.text_input(
        label="User name",
        placeholder="Enter user name",
        icon=":material/person:",
        value=selected_user.get("name"),
        disabled=(not st.session_state.get("update_user", False) and not st.session_state.get("new_user", False))
        or (st.session_state["no_users_in_selected_role"] and not st.session_state.get("new_user", False)),
    )

    return new_user_name


def input_new_user_password():
    new_user_password = st.text_input(
        label="Password",
        placeholder="Enter password",
        type="password",
        icon=":material/lock:",
        disabled=(not st.session_state.get("update_user", False) and not st.session_state.get("new_user", False))
        or (st.session_state["no_users_in_selected_role"] and not st.session_state.get("new_user", False)),
    )

    return new_user_password


def input_new_user_role_id(selected_role: dict, roles: list):
    user_role_index = [role["name"] for role in roles].index(selected_role["name"])
    new_user_role_name = st.selectbox(
        label="Role",
        options=[role["name"] for role in roles],
        key="create_user_role",
        index=user_role_index,
        disabled=(not st.session_state.get("update_user", False))
        or (st.session_state["no_users_in_selected_role"] and not st.session_state.get("new_user", False)),
    )
    new_user_role_id = [role["id"] for role in roles if role["name"] == new_user_role_name][0] if new_user_role_name else None

    return new_user_role_id


def input_new_user_budget(selected_user: dict):
    disabled = (not st.session_state.get("update_user", False) and not st.session_state.get("new_user", False)) or (st.session_state["no_users_in_selected_role"] and not st.session_state.get("new_user", False))  # fmt: off
    no_budget = st.toggle(label="No budget", key="create_user_no_budget", value=selected_user.get("budget") is None, disabled=disabled)
    new_user_budget = st.number_input(
        label="Budget", key="create_user_budget", value=selected_user.get("budget"), disabled=disabled or no_budget, icon=":material/paid:"
    )
    new_user_budget = None if no_budget else new_user_budget

    return new_user_budget


def input_new_user_expires_at(selected_user: dict):
    disabled = (not st.session_state.get("update_user", False) and not st.session_state.get("new_user", False)) or (st.session_state["no_users_in_selected_role"] and not st.session_state.get("new_user", False))  # fmt: off
    expires_at = pd.to_datetime(selected_user["expires_at"], unit="s") if selected_user else None
    no_expiration = st.toggle(label="No expiration", key="create_user_no_expiration", value=expires_at is None, disabled=disabled)
    new_user_expires_at = st.date_input(label="Expires at", key="create_user_expires_at", value=expires_at, disabled=disabled or no_expiration)
    new_user_expires_at = None if no_expiration or pd.isna(new_user_expires_at) else int(pd.Timestamp(new_user_expires_at).timestamp())

    return new_user_expires_at
