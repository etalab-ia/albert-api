import pandas as pd
import streamlit as st

from ui.backend.admin import create_role, create_user, delete_role, delete_user, update_role, update_user
from ui.frontend.header import header
from ui.backend.common import get_limits, get_models, get_roles, get_users
from ui.variables import ADMIN_PERMISSIONS

header()

if not all(perm in st.session_state["user"].role["permissions"] for perm in ADMIN_PERMISSIONS):
    st.info("Access denied.")
    st.stop()

tab1, tab2 = st.tabs(["Roles", "Users"])
with tab1:
    if not all(perm in st.session_state["user"].role["permissions"] for perm in ADMIN_PERMISSIONS):
        st.info("Access denied.")
        st.stop()

    users = get_users()
    roles = get_roles()
    models = get_models()

    with st.sidebar:
        if st.button(label="**:material/refresh: Refresh data**", key="refresh-sidebar-account", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.dataframe(
        data=pd.DataFrame(
            data={
                "ID": [role["id"] for role in roles],
                "Name": [role["name"] for role in roles],
                "Default": [role["default"] for role in roles],
                "Users": [role["users"] for role in roles],
                "Created at": [pd.to_datetime(role["created_at"], unit="s") for role in roles],
                "Updated at": [pd.to_datetime(role["updated_at"], unit="s") for role in roles],
            },
        ),
        hide_index=True,
        use_container_width=True,
        column_config={
            "ID": st.column_config.TextColumn(label="ID"),
            "Name": st.column_config.ListColumn(label="Name"),
            "Default": st.column_config.CheckboxColumn(label="Default"),
            "Created at": st.column_config.DatetimeColumn(format="D MMM YYYY", disabled=True),
            "Updated at": st.column_config.DatetimeColumn(format="D MMM YYYY", disabled=True),
        },
    )

    name = st.selectbox(label="**Select a role**", options=[role["name"] for role in roles], disabled=st.session_state.get("new_role_button", False))
    st.button(
        label="**Or create a new role**",
        on_click=lambda: setattr(st.session_state, "new_role_button", not st.session_state.get("new_role_button", False)),
        use_container_width=True,
    )
    if not st.session_state.get("new_role_button", False) and roles:
        role = [role for role in roles if role["name"] == name][0]
    else:
        role = {"name": None, "default": False, "permissions": [], "limits": []}
    new_name = st.text_input(label="Role name", placeholder="Enter role name", value=role["name"])
    default = st.toggle(label="Default", key="update_role_default", value=role["default"], help="If true, this role will be assigned to new users by default.")  # fmt: off

    st.subheader(f"Permissions of the {"*new*" if st.session_state.get("new_role_button", False) else f"*{role["name"]}*"} role")
    col1, col2, col3 = st.columns(spec=3)
    permissions = []
    with col1:
        st.caption("Roles")
        if st.checkbox(label="Create role", key="create_role", value="create_role" in role["permissions"]):
            permissions.append("create_role")
        if st.checkbox(label="Read role", key="read_role", value="read_role" in role["permissions"]):
            permissions.append("read_role")
        if st.checkbox(label="Delete role", key="delete_role", value="delete_role" in role["permissions"]):
            permissions.append("delete_role")
        if st.checkbox(label="Update role", key="update_role", value="update_role" in role["permissions"]):
            permissions.append("update_role")

    with col2:
        st.caption("Users")
        if st.checkbox(label="Create user", key="create_user", value="create_user" in role["permissions"]):
            permissions.append("create_user")
        if st.checkbox(label="Read user", key="read_user", value="read_user" in role["permissions"]):
            permissions.append("read_user")
        if st.checkbox(label="Delete user", key="delete_user", value="delete_user" in role["permissions"]):
            permissions.append("delete_user")
        if st.checkbox(label="Update user", key="update_user", value="update_user" in role["permissions"]):
            permissions.append("update_user")

    with col3:
        st.caption("Others")
        if st.checkbox(label="Read metric", key="read_metric", value="read_metric" in role["permissions"]):
            permissions.append("read_metric")
        create_public_collection = st.checkbox(label="Create public collection", key="create_public_collection", value="create_public_collection" in role["permissions"])  # fmt: off
        if create_public_collection:
            permissions.append("create_public_collection")

    st.subheader(f"Rate limits of the {"*new*" if st.session_state.get("new_role_button", False) else f"*{role["name"]}*"} role")
    limits = get_limits(models=models, role=role)
    initial_limits = pd.DataFrame(
        data={
            "Request per minute": [limits[model]["rpm"] for model in models],
            "Request per day": [limits[model]["rpd"] for model in models],
            "Tokens per minute": [limits[model]["tpm"] for model in models],
        },
        index=models,
    )

    edited_limits = initial_limits.copy()
    edited_limits = st.data_editor(
        data=edited_limits,
        use_container_width=True,
        disabled=["_index"],
        column_config={
            "Request per minute": st.column_config.NumberColumn(label="Request per minute", min_value=0, step=1, required=False),
            "Request per day": st.column_config.NumberColumn(label="Request per day", min_value=0, step=1, required=False),
            "Tokens per minute": st.column_config.NumberColumn(label="Tokens per minute", min_value=0, step=1, required=False),
        },
    )

    col1, col2, col3 = st.columns(spec=3)
    with col1:
        if st.button(
            label="**:material/add: Add**",
            key="add_limits_button",
            use_container_width=True,
            disabled=not st.session_state.get("new_role_button", False),
        ):
            limits = []
            for model, row in edited_limits.iterrows():
                for type in row.index:
                    value = None if pd.isna(row[type]) else int(row[type])
                    type = "tpm" if type == "Tokens per minute" else type
                    type = "rpm" if type == "Request per minute" else type
                    type = "rpd" if type == "Request per day" else type
                    limits.append({"model": model, "type": type, "value": value})

            create_role(name=new_name, permissions=permissions, limits=limits, default=default)

    with col2:
        if st.button(
            label="**:material/update: Update**",
            key="update_limits_button",
            use_container_width=True,
            disabled=st.session_state.get("new_role_button", False) or not roles,
        ):
            limits = []
            for model, row in edited_limits.iterrows():
                for type in row.index:
                    value = None if pd.isna(row[type]) else int(row[type])
                    type = "tpm" if type == "Tokens per minute" else type
                    type = "rpm" if type == "Request per minute" else type
                    type = "rpd" if type == "Request per day" else type
                    limits.append({"model": model, "type": type, "value": value})
            update_role(role=role["id"], name=new_name, permissions=permissions, limits=limits, default=default)

    with col3:
        if st.button(
            label="**:material/delete_forever: Delete**",
            key="delete_role_button",
            use_container_width=True,
            disabled=st.session_state.get("new_role_button", False) or not roles,
        ):
            delete_role(role=role["id"])

with tab2:
    roles_dict = {role["id"]: role["name"] for role in roles}
    st.dataframe(
        data=pd.DataFrame(
            data={
                "ID": [user["id"] for user in users],
                "Name": [user["name"] for user in users],
                "Role": [roles_dict[user["role"]] for user in users],
                "Access UI": [user["access_ui"] for user in users],
                "Expires at": [pd.to_datetime(user["expires_at"], unit="s") if user["expires_at"] else None for user in users],
                "Created at": [pd.to_datetime(user["created_at"], unit="s") for user in users],
                "Updated at": [pd.to_datetime(user["updated_at"], unit="s") for user in users],
            }
        ),
        hide_index=True,
        use_container_width=True,
        column_config={
            "ID": st.column_config.TextColumn(label="ID"),
            "Name": st.column_config.ListColumn(label="Name"),
            "Role": st.column_config.ListColumn(label="Role"),
            "Access UI": st.column_config.CheckboxColumn(label="Access UI", help="If true, the user has created by the admin UI."),
            "Expires at": st.column_config.DatetimeColumn(format="D MMM YYYY"),
            "Created at": st.column_config.DatetimeColumn(format="D MMM YYYY"),
            "Updated at": st.column_config.DatetimeColumn(format="D MMM YYYY"),
        },
    )

    name = st.selectbox(label="**Select a user**", options=[user["name"] for user in users], disabled=st.session_state.get("new_user_button", False))
    st.button(
        label="**Create a new user**",
        on_click=lambda: setattr(st.session_state, "new_user_button", not st.session_state.get("new_user_button", False)),
        use_container_width=True,
    )

    role_names = [role["name"] for role in roles]
    default_role = [role["name"] for role in roles if role["default"]]
    default_role = default_role[0] if default_role else None
    default_role_index = role_names.index(default_role) if default_role else None

    if not st.session_state.get("new_user_button", False) and users:
        user = [user for user in users if user["name"] == name][0]
    else:
        user = {"name": None, "role": default_role, "expires_at": None}

    new_name = st.text_input(label="User name", placeholder="Enter user name", value=user["name"])
    new_password = st.text_input(label="Password", placeholder="Enter password", type="password")

    user_role = [role["name"] for role in roles if role["id"] == user["role"]]
    user_role = user_role[0] if user_role else None
    user_role_index = role_names.index(user_role) if user_role else None
    role_index = default_role_index if st.session_state.get("new_user_button", False) else user_role_index
    role_name = st.selectbox(label="Role", options=[role["name"] for role in roles], key="create_user_role", index=role_index)
    new_role = [role["id"] for role in roles if role["name"] == role_name][0] if role_name else None

    expires_at = pd.to_datetime(user["expires_at"], unit="s") if user["expires_at"] else None
    no_expiration = st.toggle(label="No expiration", key="create_user_no_expiration", value=expires_at is None)
    new_expires_at = st.date_input(label="Expires at", key="create_user_expires_at", min_value=pd.Timestamp.now(), value=expires_at, disabled=no_expiration)  # fmt: off
    new_expires_at = None if no_expiration or pd.isna(new_expires_at) else int(pd.Timestamp(new_expires_at).timestamp())

    col1, col2, col3 = st.columns(spec=3)

    with col1:
        if st.button(
            label="**:material/add: Add**",
            key="add_user_button",
            use_container_width=True,
            disabled=not st.session_state.get("new_user_button", False) or not roles,
        ):
            create_user(name=new_name, password=new_password, role=new_role, expires_at=new_expires_at)

    with col2:
        if st.button(
            label="**:material/update: Update**",
            key="update_user_button",
            use_container_width=True,
            disabled=st.session_state.get("new_user_button", False) or not users or not user["access_ui"],
        ):
            update_user(user=user["id"], name=new_name, password=new_password, role=new_role, expires_at=new_expires_at)

    with col3:
        if st.button(
            label="**:material/delete_forever: Delete**",
            key="delete_user_button",
            use_container_width=True,
            disabled=st.session_state.get("new_user_button", False) or not users,
        ):
            delete_user(user=user["id"])
