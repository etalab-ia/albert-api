import pandas as pd
import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from ui.backend.admin import create_role, create_user, delete_role, delete_user, refresh_playground_api_key, update_role, update_user
from ui.backend.common import get_limits, get_models
from ui.frontend.header import header
from ui.frontend.utils import ressources_selector
from ui.variables import ADMIN_PERMISSIONS

header()

if not all(perm in st.session_state["user"].role["permissions"] for perm in ADMIN_PERMISSIONS):
    st.info("Access denied.")
    st.stop()


models = get_models()

with st.expander(label="Roles", expanded=not st.session_state.get("new_role", False)):
    roles, selected_role = ressources_selector(ressource="role")

with st.sidebar:
    st.subheader("**Roles**")

    st.button(
        label="**:material/add: Create role**",
        key="create_new_role",
        on_click=lambda: setattr(st.session_state, "new_role", not st.session_state.get("new_role", False)),
        use_container_width=True,
        type="primary" if st.session_state.get("new_role", False) else "secondary",
    )
    if st.button(
        label="**:material/update: Update selected role**",
        key="update_role_button",
        use_container_width=True,
        disabled=st.session_state.get("new_role", False) or not roles,
    ):
        update_role(
            role=selected_role["id"],
            name=st.session_state.get("new_name"),
            permissions=st.session_state.get("permissions"),
            limits=st.session_state.get("limits"),
        )

    if st.button(
        label="**:material/delete_forever: Delete selected role**",
        key="delete_role_button",
        use_container_width=True,
        disabled=st.session_state.get("new_role", False) or not roles,
    ):
        delete_role(role=selected_role["id"])

    st.subheader("**Users**")

if not roles and not st.session_state.get("new_role", False):
    st.warning("No roles found. Please create a new role.")
    st.stop()

new_role_name = st.text_input(label="Role name", placeholder="Enter role name", value=selected_role["name"])

st.markdown(body=f"#### Permissions of the *{"new" if st.session_state.get("new_role", False) else selected_role["name"]}* role")
col1, col2, col3 = st.columns(spec=3)
permissions = []
with col1:
    st.caption("Roles")
    if st.checkbox(label="Create role", key="create_role", value="create_role" in selected_role["permissions"]):
        permissions.append("create_role")
    if st.checkbox(label="Read role", key="read_role", value="read_role" in selected_role["permissions"]):
        permissions.append("read_role")
    if st.checkbox(label="Delete role", key="delete_role", value="delete_role" in selected_role["permissions"]):
        permissions.append("delete_role")
    if st.checkbox(label="Update role", key="update_role", value="update_role" in selected_role["permissions"]):
        permissions.append("update_role")

with col2:
    st.caption("Users")
    if st.checkbox(label="Create user", key="create_user", value="create_user" in selected_role["permissions"]):
        permissions.append("create_user")
    if st.checkbox(label="Read user", key="read_user", value="read_user" in selected_role["permissions"]):
        permissions.append("read_user")
    if st.checkbox(label="Delete user", key="delete_user", value="delete_user" in selected_role["permissions"]):
        permissions.append("delete_user")
    if st.checkbox(label="Update user", key="update_user", value="update_user" in selected_role["permissions"]):
        permissions.append("update_user")

with col3:
    st.caption("Others")
    if st.checkbox(label="Read metric", key="read_metric", value="read_metric" in selected_role["permissions"]):
        permissions.append("read_metric")
    create_public_collection = st.checkbox(label="Create public collection", key="create_public_collection", value="create_public_collection" in selected_role["permissions"])  # fmt: off
    if create_public_collection:
        permissions.append("create_public_collection")

st.markdown(body=f"#### Rate limits of the *{"new" if st.session_state.get("new_role", False) else selected_role["name"]}* role")
limits = get_limits(models=models, role=selected_role)
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
    disabled=["_index"],
    column_config={
        "_index": st.column_config.ListColumn(label="", width="large"),
        "Request per minute": st.column_config.NumberColumn(label="Request per minute", min_value=0, step=1, required=False, width="small"),
        "Request per day": st.column_config.NumberColumn(label="Request per day", min_value=0, step=1, required=False, width="small"),
        "Tokens per minute": st.column_config.NumberColumn(label="Tokens per minute", min_value=0, step=1, required=False, width="small"),
        "Tokens per day": st.column_config.NumberColumn(label="Tokens per day", min_value=0, step=1, required=False, width="small"),
    },
    height=28 * len(models) + 37,
    row_height=28,
)
limits = []
for model, row in edited_limits.iterrows():
    for type in row.index:
        value = None if pd.isna(row[type]) else int(row[type])
        type = "tpm" if type == "Tokens per minute" else type
        type = "tpd" if type == "Tokens per day" else type
        type = "rpm" if type == "Request per minute" else type
        type = "rpd" if type == "Request per day" else type
        limits.append({"model": model, "type": type, "value": value})

st.session_state["new_role_name"] = new_role_name
st.session_state["permissions"] = permissions
st.session_state["limits"] = limits

if st.session_state.get("new_role", False):
    with stylable_container(key="Header", css_styles="button{float: right;}"):
        if st.button(label="**Create**", key="validate_role_button"):
            limits = []
            for model, row in edited_limits.iterrows():
                for type in row.index:
                    value = None if pd.isna(row[type]) else int(row[type])
                    type = "tpm" if type == "Tokens per minute" else type
                    type = "tpd" if type == "Tokens per day" else type
                    type = "rpm" if type == "Request per minute" else type
                    type = "rpd" if type == "Request per day" else type
                    limits.append({"model": model, "type": type, "value": value})
            create_role(name=st.session_state.get("new_role_name"), permissions=permissions, limits=limits)

# Users
if not roles or st.session_state.get("new_role", False):
    st.stop()

st.markdown(body=f"#### Users of the *{"new" if st.session_state.get("new_role", False) else selected_role["name"]}* role")
with st.expander(label="Users", expanded=not st.session_state.get("new_user", False)):
    users, selected_user = ressources_selector(ressource="user", filter=selected_role["id"])

with st.sidebar:
    st.button(
        label="**:material/add: Create user**",
        on_click=lambda: setattr(st.session_state, "new_user", not st.session_state.get("new_user", False)),
        use_container_width=True,
        type="primary" if st.session_state.get("new_user", False) else "secondary",
    )
    if st.button(
        label="**:material/update: Update selected user**",
        key="update_user_button",
        use_container_width=True,
        disabled=st.session_state.get("new_user", False) or not users,
    ):
        update_user(
            user=st.session_state.get("new_user_id"),
            name=st.session_state.get("new_name"),
            password=st.session_state.get("new_password"),
            role=st.session_state.get("new_role_id"),
            expires_at=st.session_state.get("new_expires_at"),
        )

    if st.button(
        label="**:material/delete_forever: Delete selected user**",
        key="delete_user_button",
        use_container_width=True,
        disabled=st.session_state.get("new_user", False) or not users,
    ):
        delete_user(user=selected_user.get("id"))

    if st.button(
        label="**:material/key: Refresh playground key of selected user**",
        key="refresh_playground_user_api_key_button",
        use_container_width=True,
        disabled=st.session_state.get("new_user", False) or not users,
    ):
        refresh_playground_api_key(user=selected_user["id"])


if not users and not st.session_state.get("new_user", False):
    st.warning("No users found. Please create a new user.")
    st.stop()


new_user_name = st.text_input(label="User name", placeholder="Enter user name", value=selected_user["name"])
new_user_password = st.text_input(label="Password", placeholder="Enter password", type="password")

user_role = [role for role in roles if role["id"] == selected_user["role"]]
user_role = user_role[0] if user_role else selected_role
user_role_name, user_role_id = user_role["name"], user_role["id"]
user_role_index = [role["name"] for role in roles].index(user_role_name)

new_user_role_name = st.selectbox(
    label="Role",
    options=[role["name"] for role in roles],
    key="create_user_role",
    index=user_role_index,
    disabled=st.session_state.get("new_user", False),
)
new_user_role_id = [role["id"] for role in roles if role["name"] == new_user_role_name][0] if new_user_role_name else None

expires_at = pd.to_datetime(selected_user["expires_at"], unit="s") if selected_user["expires_at"] else None
no_expiration = st.toggle(label="No expiration", key="create_user_no_expiration", value=expires_at is None)
new_user_expires_at = st.date_input(label="Expires at", key="create_user_expires_at", value=expires_at, disabled=no_expiration)
new_user_expires_at = None if no_expiration or pd.isna(new_user_expires_at) else int(pd.Timestamp(new_user_expires_at).timestamp())

st.session_state["new_user_name"] = new_user_name
st.session_state["new_user_password"] = new_user_password
st.session_state["new_user_role_id"] = new_user_role_id
st.session_state["new_user_expires_at"] = new_user_expires_at

if st.session_state.get("new_user", False):
    with stylable_container(key="Header", css_styles="button{float: right;}"):
        if st.button(label="**Create**", key="add_user_button"):
            create_user(
                name=st.session_state.get("new_name"),
                password=st.session_state.get("new_password"),
                role=st.session_state.get("new_role_id"),
                expires_at=st.session_state.get("new_expires_at"),
            )
