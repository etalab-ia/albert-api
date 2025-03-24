import pandas as pd
import streamlit as st

from ui.backend.admin import create_role, create_user, delete_role, delete_user, update_role, update_user
from ui.frontend.header import header
from utils.common import get_limits, get_models, get_roles, get_users
from utils.variables import ADMIN_PERMISSIONS, MODEL_TYPE_LANGUAGE

header()

if not all(perm in st.session_state["user"].role["permissions"] for perm in ADMIN_PERMISSIONS):
    st.info("Access denied.")
    st.stop()

users = get_users()
roles = get_roles()
models = get_models(type=MODEL_TYPE_LANGUAGE, api_key=st.session_state["user"].api_key)

with st.sidebar:
    if st.button(label="**:material/refresh: Refresh data**", key="refresh-sidebar-account", use_container_width=True):
        st.cache_data.clear()

st.subheader("Roles")
st.dataframe(
    data=pd.DataFrame(
        data={
            "ID": [role["id"] for role in roles],
            "Name": [role["name"] for role in roles],
            "Default": [role["default"] for role in roles],
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

if len(roles) == 0:
    st.stop()

new_role = st.toggle(label="Create a new role", key="create_role_button")
name = st.selectbox(label="**Select a role**", options=[role["name"] for role in roles], disabled=new_role)
role = [role for role in roles if role["name"] == name][0] if not new_role else {"default": False, "name": "my-role", "permissions": [], "limits": []}

new_name = st.text_input(label="Role name", placeholder="Enter role name", value=role["name"])
default = st.toggle(label="Default", key="update_role_default", value=role["default"], help="If true, this role will be assigned to new users by default.")  # fmt: off

st.write("**Admin permissions**")
col1, col2, col3, col4 = st.columns(spec=4)
permissions = []
with col1:
    if st.checkbox(label="Create role", key="create_role", value="create_role" in role["permissions"]):
        permissions.append("create_role")
    if st.checkbox(label="Read role", key="read_role", value="read_role" in role["permissions"]):
        permissions.append("read_role")
    if st.checkbox(label="Delete role", key="delete_role", value="delete_role" in role["permissions"]):
        permissions.append("delete_role")
    if st.checkbox(label="Update role", key="update_role", value="update_role" in role["permissions"]):
        permissions.append("update_role")

with col2:
    if st.checkbox(label="Create user", key="create_user", value="create_user" in role["permissions"]):
        permissions.append("create_user")
    if st.checkbox(label="Read user", key="read_user", value="read_user" in role["permissions"]):
        permissions.append("read_user")
    if st.checkbox(label="Delete user", key="delete_user", value="delete_user" in role["permissions"]):
        permissions.append("delete_user")
    if st.checkbox(label="Update user", key="update_user", value="update_user" in role["permissions"]):
        permissions.append("update_user")

with col3:
    if st.checkbox(label="Create token", key="create_token", value="create_token" in role["permissions"]):
        permissions.append("create_token")
    if st.checkbox(label="Read token", key="read_token", value="read_token" in role["permissions"]):
        permissions.append("read_token")
    if st.checkbox(label="Delete token", key="delete_token", value="delete_token" in role["permissions"]):
        permissions.append("delete_token")

with col4:
    if st.checkbox(label="Read metric", key="read_metric", value="read_metric" in role["permissions"]):
        permissions.append("read_metric")
    create_public_collection = st.checkbox(label="Create public collection", key="create_public_collection", value="create_public_collection" in role["permissions"])  # fmt: off
    if create_public_collection:
        permissions.append("create_public_collection")

st.write("**Model rate limits**")
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
    if st.button(label="**:material/add: Add**", key="add_limits_button", use_container_width=True, disabled=not new_role):
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
    if st.button(label="**:material/update: Update**", key="update_limits_button", use_container_width=True, disabled=new_role):
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
    if st.button(label="**:material/delete_forever: Delete**", key="delete_role_button", use_container_width=True, disabled=new_role):
        delete_role(role=role["id"])

st.divider()
st.subheader("Users")

roles_dict = {role["id"]: role["name"] for role in roles}
st.dataframe(
    data=pd.DataFrame(
        data={
            "ID": [user["id"] for user in users],
            "Name": [user["name"] for user in users],
            "Role": [roles_dict[user["role"]] for user in users],
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
        "Expires at": st.column_config.DatetimeColumn(format="D MMM YYYY"),
        "Created at": st.column_config.DatetimeColumn(format="D MMM YYYY"),
        "Updated at": st.column_config.DatetimeColumn(format="D MMM YYYY"),
    },
)

col1, col2, col3 = st.columns(spec=3)

with col1:
    with st.expander(label="Create a user", icon=":material/add_circle:"):
        name = st.text_input(label="User name", placeholder="my-user", key="create_user_id")
        default_role_index = [i for i, r in enumerate(roles) if r["default"]]
        default_role_index = None if len(default_role_index) == 0 else default_role_index[0]
        password = st.text_input(label="Password", placeholder="my-password", type="password", key="create_user_password")
        role_name = st.selectbox(label="Role", options=[role["name"] for role in roles], key="create_user_role", index=default_role_index)
        role = [role["id"] for r in roles if r["name"] == role_name][0]["id"] if role_name else None
        expires_at = st.date_input(label="Expires at", key="create_user_expires_at", min_value=pd.Timestamp.now(), value=None)
        expires_at = None if expires_at is None else int(pd.Timestamp(expires_at).timestamp())
        if st.button(label="Create", disabled=not name or not password or not role, key="create_user_button"):
            create_user(name=name, password=password, role=role, expires_at=expires_at)

with col2:
    with st.expander(label="Delete a user", icon=":material/delete_forever:"):
        name = st.selectbox(label="User", options=[user["name"] for user in users], key="delete_user_name")
        user = [user["id"] for user in users if user["name"] == name][0] if name else None
        if st.button(label="Delete", disabled=not user, key="delete_user_button"):
            delete_user(user=user)

with col3:
    with st.expander(label="Update a user", icon=":material/update:"):
        name = st.selectbox(label="User", options=[user["name"] for user in users], key="update_user_name")
        user = [user for user in users if user["name"] == name][0] if name else None
        if not user:
            st.stop()

        new_user = st.text_input(label="User ID", placeholder="my-user", key="update_user_user", value=user["id"])
        new_password = st.text_input(label="Password", placeholder="my-password", type="password", key="update_user_password", value=None)
        new_role_name = st.selectbox(
            label="Role",
            options=[role["name"] for role in roles],
            key="update_user_role",
            index=[i for i, role in enumerate(roles) if role["name"] == user["role"]][0],
        )
        new_role = [role["id"] for role in roles if role["name"] == new_role_name][0]["id"]
        expires_at = st.date_input(label="Expires at", key="update_user_expires_at", min_value=pd.Timestamp.now(), value=None)
        expires_at = None if expires_at is None else int(pd.Timestamp(expires_at).timestamp())
        if st.button(label="Update", disabled=not user, key="update_user_button"):
            update_user(user_id=user["id"], user=new_user, password=new_password, role=new_role, expires_at=expires_at)
