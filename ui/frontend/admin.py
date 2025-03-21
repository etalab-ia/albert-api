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

col1, col2 = st.columns(spec=2)

with col1:
    with st.expander(label="Create a role", icon=":material/add_circle:"):
        role = st.text_input(label="Role ID", placeholder="my-role", help="ID of the role to create.")
        _col1, _col2 = st.columns(spec=2)
        with _col1:
            default = st.toggle(label="Default", key="create_role_default", value=False)

        submit_create = st.button(label="Create", disabled=not role)
        if submit_create:
            create_role(role=role, default=default)


with col2:
    with st.expander(label="Delete a role", icon=":material/delete_forever:"):
        role = st.selectbox(label="Role ID", options=[role["id"] for role in roles])
        if st.button(label="Delete", disabled=not role, key="delete_role_button"):
            delete_role(role=role)


if len(roles) == 0:
    st.stop()

st.markdown("##### Update a role")

if role := st.selectbox(label="**Select a role**", options=[role["id"] for role in roles]):
    role = [r for r in roles if r["id"] == role][0]

    col1, col2 = st.columns(spec=2)
    with col1:
        default = st.toggle(label="Default", key="update_role_default", value=role["default"])
    with col2:
        admin = st.toggle(label="Admin", key="update_role_admin", value=all(perm in role["permissions"] for perm in ADMIN_PERMISSIONS))

    st.write("**Admin permissions**")

    initial_permissions = pd.DataFrame(
        index=["Create", "Read", "Update", "Delete"],
        columns=["Private collection", "Public collection", "Role", "User", "Token", "Metric"],
    )
    for permission in role["permissions"]:
        action, subject = permission.split("_")[0].title(), " ".join(permission.split("_")[1:]).capitalize()
        initial_permissions.loc[action, subject] = True
    initial_permissions = initial_permissions.fillna(False)

    edited_permissions = initial_permissions.copy()
    edited_permissions = st.data_editor(
        data=edited_permissions,
        disabled=["_index"],
        use_container_width=True,
        column_config={
            "Private collection": st.column_config.CheckboxColumn(label="Private collection"),
            "Public collection": st.column_config.CheckboxColumn(label="Public collection"),
            "Role": st.column_config.CheckboxColumn(label="Role", disabled=True),
            "User": st.column_config.CheckboxColumn(label="User", disabled=True),
            "Token": st.column_config.CheckboxColumn(label="Token", disabled=True),
            "Metric": st.column_config.CheckboxColumn(label="Metric", disabled=True),
        },
        column_order=["Private collection", "Public collection", "Role", "User", "Token", "Metric"],
    )

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

    if st.button(label="Update", key="update_limits_button"):
        permissions = ADMIN_PERMISSIONS if admin else []
        for action, row in edited_permissions.iterrows():
            for subject in row.index:
                permission = f"{action.lower()}_{subject.lower().replace(" ", "_")}"
                if row[subject] and "collection" in permission:
                    permissions.append(permission)

        limits = []
        for model, row in edited_limits.iterrows():
            for type in row.index:
                value = None if pd.isna(row[type]) else int(row[type])
                type = "tpm" if type == "Tokens per minute" else type
                type = "rpm" if type == "Request per minute" else type
                type = "rpd" if type == "Request per day" else type
                limits.append({"model": model, "type": type, "value": value})
        update_role(role_id=role["id"], permissions=permissions, limits=limits, default=default)

st.divider()
st.subheader("Users")

st.dataframe(
    data=pd.DataFrame(
        data={
            "ID": [user["id"] for user in users],
            "Role": [user["role"] for user in users],
            "Expires at": [pd.to_datetime(user["expires_at"], unit="s") if user["expires_at"] else None for user in users],
            "Created at": [pd.to_datetime(user["created_at"], unit="s") for user in users],
            "Updated at": [pd.to_datetime(user["updated_at"], unit="s") for user in users],
        }
    ),
    hide_index=True,
    use_container_width=True,
    column_config={
        "ID": st.column_config.ListColumn(label="ID"),
        "Role": st.column_config.ListColumn(label="Role"),
        "Expires at": st.column_config.DatetimeColumn(format="D MMM YYYY"),
        "Created at": st.column_config.DatetimeColumn(format="D MMM YYYY"),
        "Updated at": st.column_config.DatetimeColumn(format="D MMM YYYY"),
    },
)

col1, col2, col3 = st.columns(spec=3)

with col1:
    with st.expander(label="Create a user", icon=":material/add_circle:"):
        user = st.text_input(label="User ID", placeholder="my-user", key="create_user_id")
        default_role_index = [i for i, r in enumerate(roles) if r["default"]]
        default_role_index = None if len(default_role_index) == 0 else default_role_index[0]
        password = st.text_input(label="Password", placeholder="my-password", type="password", key="create_user_password")
        role = st.selectbox(label="Role", options=[role["id"] for role in roles], key="create_user_role", index=default_role_index)
        expires_at = st.date_input(label="Expires at", key="create_user_expires_at", min_value=pd.Timestamp.now(), value=None)
        if st.button(label="Create", disabled=not user or not password or not role, key="create_user_button"):
            create_user(user=user, password=password, role=role, expires_at=expires_at)

with col2:
    with st.expander(label="Delete a user", icon=":material/delete_forever:"):
        user = st.selectbox(label="User ID", options=[user["id"] for user in users], key="delete_user_id")
        if st.button(label="Delete", disabled=not user, key="delete_user_button"):
            delete_user(user=user)

with col3:
    with st.expander(label="Update a user", icon=":material/update:"):
        user_id = st.selectbox(label="User", options=[user["id"] for user in users], key="update_user_id")
        if not user_id:
            st.stop()
        user = [u for u in users if u["id"] == user_id][0]
        role = [r for r in roles if r["id"] == user["role"]][0]["id"]
        new_user = st.text_input(label="User ID", placeholder="my-user", key="update_user_user", value=user["id"])
        new_password = st.text_input(label="Password", placeholder="my-password", type="password", key="update_user_password", value=None)
        new_role = st.selectbox(
            label="Role",
            options=[role["id"] for role in roles],
            key="update_user_role",
            index=[i for i, r in enumerate(roles) if r["id"] == role][0],
        )
        expires_at = st.date_input(label="Expires at", key="update_user_expires_at", min_value=pd.Timestamp.now(), value=None)
        expires_at = None if expires_at is None else int(pd.Timestamp(expires_at).timestamp())
        if st.button(label="Update", disabled=not user_id, key="update_user_button"):
            update_user(user_id=user_id, user=new_user, password=new_password, role=new_role, expires_at=expires_at)
