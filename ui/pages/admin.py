import re
import time
from typing import Optional

import pandas as pd
import requests
import streamlit as st

from utils.common import clear_cache, get_models, get_roles, get_users, header, settings
from utils.variables import MODEL_TYPE_LANGUAGE


def create_role(role: str, default: bool, admin: bool):
    response = requests.post(
        url=f"{settings.api_url}/roles",
        headers={"Authorization": f"Bearer {settings.api_key}"},
        json={"role": role, "default": default, "admin": admin},
    )
    if response.status_code == 201:
        st.toast("Role created", icon="✅")
        get_roles.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast("Role creation failed", icon="❌")


def delete_role(role: str):
    response = requests.delete(url=f"{settings.api_url}/roles/{role}", headers={"Authorization": f"Bearer {settings.api_key}"})
    if response.status_code == 204:
        st.toast("Role deleted", icon="✅")
        get_roles.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast("Role deletion failed", icon="❌")


def update_role(role_id: str, role: Optional[str] = None, default: Optional[bool] = None, admin: Optional[bool] = None):
    response = requests.patch(
        url=f"{settings.api_url}/roles/{role_id}",
        json={"role": role, "default": default, "admin": admin},
        headers={"Authorization": f"Bearer {settings.api_key}"},
    )
    if response.status_code == 201:
        st.toast("Role updated", icon="✅")
        get_roles.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast("Role update failed", icon="❌")


def update_limits(role: str, limits: list):
    response = requests.patch(
        url=f"{settings.api_url}/roles/{role}",
        json={"limits": limits},
        headers={"Authorization": f"Bearer {settings.api_key}"},
    )
    if response.status_code == 201:
        st.toast("Limits updated", icon="✅")
        get_roles.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast("Limits update failed", icon="❌")


def create_user(
    user: str,
    password: str,
    role: str,
):
    response = requests.post(
        url=f"{settings.api_url}/users",
        json={"user": user, "password": password, "role": role},
        headers={"Authorization": f"Bearer {settings.api_key}"},
    )
    if response.status_code == 201:
        st.toast("User created", icon="✅")
        get_users.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast("User creation failed", icon="❌")


def delete_user(user: str):
    response = requests.delete(url=f"{settings.api_url}/users/{user}", headers={"Authorization": f"Bearer {settings.api_key}"})
    if response.status_code == 204:
        st.toast("User deleted", icon="✅")
        get_users.clear()
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast("User deletion failed", icon="❌")


def update_user(
    user_id: str,
    user: Optional[str] = None,
    password: Optional[str] = None,
    role: Optional[str] = None,
):
    response = requests.patch(
        url=f"{settings.api_url}/users/{user_id}",
        json={"user": user, "password": password, "role": role},
        headers={"Authorization": f"Bearer {settings.api_key}"},
    )
    if response.status_code == 201:
        st.toast("User updated", icon="✅")
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast("User update failed", icon="❌")


header()

if not st.session_state["user"]["role"]["admin"]:
    st.info("Access denied.")
    st.stop()

users = get_users()
roles = get_roles()
models = get_models(type=MODEL_TYPE_LANGUAGE, api_key=settings.api_key)


with st.sidebar:
    if st.button(label="**:material/refresh: Refresh data**", key="refresh-sidebar-account", use_container_width=True):
        clear_cache()

st.subheader("Roles")

col1, col2 = st.columns(spec=2)

with col1:
    with st.expander(label="Create a role", icon=":material/add_circle:"):
        role = st.text_input(label="Role ID", placeholder="my-role", help="ID of the role to create.")
        _col1, _col2 = st.columns(spec=2)
        with _col1:
            default = st.toggle(label="Default", value=False)
        with _col2:
            admin = st.toggle(
                label="Admin",
                help="Admin rights: access to all models with no rate limits, manage roles, users and public collections.",
                value=False,
            )

        submit_create = st.button(label="Create", disabled=not role)
        if submit_create:
            create_role(role=role, default=default, admin=admin)


with col2:
    with st.expander(label="Delete a role", icon=":material/delete_forever:"):
        role = st.selectbox(label="Role ID", options=[role["id"] for role in roles])
        if st.button(label="Delete", disabled=not role, key="delete_role_button"):
            delete_role(role=role)


initial_roles = pd.DataFrame(
    data={
        "ID": [role["id"] for role in roles],
        "Default": [role["default"] for role in roles],
        "Admin": [role["admin"] for role in roles],
        "Created at": [pd.to_datetime(role["created_at"], unit="s") for role in roles],
        "Updated at": [pd.to_datetime(role["updated_at"], unit="s") for role in roles],
    }
)

edited_roles = initial_roles.copy()
if len(edited_roles) > 0:
    edited_roles = st.data_editor(
        data=edited_roles,
        hide_index=True,
        use_container_width=True,
        column_config={
            "ID": st.column_config.TextColumn(label="ID"),
            "Default": st.column_config.CheckboxColumn(label="Default"),
            "Admin": st.column_config.CheckboxColumn(label="Admin"),
            "Created at": st.column_config.DatetimeColumn(format="D MMM YYYY", disabled=True),
            "Updated at": st.column_config.DatetimeColumn(format="D MMM YYYY", disabled=True),
        },
    )
else:
    st.dataframe(data=initial_roles, hide_index=True, use_container_width=True)
    st.stop()

if st.button(label="Update", key="update_roles_button", disabled=edited_roles.equals(initial_roles)):
    for index, row in edited_roles.iterrows():
        if initial_roles.loc[index, "ID"] == "master":
            continue

        new_role = row["ID"] if row["ID"] != initial_roles.loc[index, "ID"] else None
        new_default = row["Default"] if row["Default"] != initial_roles.loc[index, "Default"] else None
        new_admin = row["Admin"] if row["Admin"] != initial_roles.loc[index, "Admin"] else None
        update_role(role_id=initial_roles.loc[index, "ID"], role=new_role, default=new_default, admin=new_admin)


if role := st.selectbox(label="**Rate limits**", options=[role["id"] for role in roles]):
    limits = [r["limits"] for r in roles if r["id"] == role][0]

    tpm, rpm, rpd = {}, {}, {}
    for model in models:
        tpm[model] = 0
        rpm[model] = 0
        rpd[model] = 0
        for limit in sorted(limits, key=lambda limit: len(limit["model_regex"])):
            if bool(re.match(pattern=limit["model_regex"], string=model)):
                tpm[model] = limit["tpm"]
                rpm[model] = limit["rpm"]
                rpd[model] = limit["rpd"]

    initial_limits = pd.DataFrame(
        data={
            "Model": models,
            "Request per minute": [rpm[model] for model in models],
            "Request per day": [rpd[model] for model in models],
            "Tokens per minute": [tpm[model] for model in models],
        }
    )

    edited_limits = initial_limits.copy()
    edited_limits = st.data_editor(
        data=edited_limits,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Model": st.column_config.ListColumn(label="Models"),
            "Request per minute": st.column_config.NumberColumn(label="Request per minute", min_value=0, step=1, required=False),
            "Request per day": st.column_config.NumberColumn(label="Request per day", min_value=0, step=1, required=False),
            "Tokens per minute": st.column_config.NumberColumn(label="Tokens per minute", min_value=0, step=1, required=False),
        },
    )

    if st.button(label="Update", key="update_limits_button", disabled=edited_limits.equals(initial_limits)):
        edited_limits = [
            {
                "model_regex": f"^{row["Model"]}$",
                "tpm": row["Tokens per minute"] if not pd.isna(row["Tokens per minute"]) else None,
                "rpm": row["Request per minute"] if not pd.isna(row["Request per minute"]) else None,
                "rpd": row["Request per day"] if not pd.isna(row["Request per day"]) else None,
            }
            for index, row in edited_limits.iterrows()
        ]
        update_limits(role=role, limits=edited_limits)

st.divider()
st.subheader("Users")

st.dataframe(
    data=pd.DataFrame(
        data={
            "ID": [user["id"] for user in users],
            "Role": [user["role"] for user in users],
            "Created at": [pd.to_datetime(user["created_at"], unit="s") for user in users],
            "Updated at": [pd.to_datetime(user["updated_at"], unit="s") for user in users],
        }
    ),
    hide_index=True,
    use_container_width=True,
    column_config={
        "ID": st.column_config.ListColumn(label="ID"),
        "Role": st.column_config.ListColumn(label="Role"),
        "Created at": st.column_config.DatetimeColumn(format="D MMM YYYY"),
        "Updated at": st.column_config.DatetimeColumn(format="D MMM YYYY"),
    },
)

col1, col2, col3 = st.columns(spec=3)

with col1:
    with st.expander(label="Create a user", icon=":material/add_circle:"):
        user = st.text_input(label="User ID", placeholder="my-user", key="create_user_id")
        password = st.text_input(label="Password", placeholder="my-password", type="password", key="create_user_password")
        role = st.selectbox(label="Role", options=[role["id"] for role in roles], key="create_user_role")
        if st.button(label="Create", disabled=not user, key="create_user_button"):
            create_user(user=user, password=password, role=role)

with col2:
    with st.expander(label="Delete a user", icon=":material/delete_forever:"):
        user = st.selectbox(label="User ID", options=[user["id"] for user in users], key="delete_user_id")
        if st.button(label="Delete", disabled=not user, key="delete_user_button"):
            delete_user(user=user)

with col3:
    with st.expander(label="Update a user", icon=":material/update:"):
        user_id = st.selectbox(label="User ID", options=[user["id"] for user in users], key="update_user_id")
        user = st.text_input(label="User", placeholder="my-user", key="update_user_user")
        password = st.text_input(label="Password", placeholder="my-password", type="password", key="update_user_password")
        role = st.selectbox(label="Role", options=[role["id"] for role in roles], key="update_user_role")
        if st.button(label="Update", disabled=not user, key="update_user_button"):
            update_user(user_id=user_id, user=user, password=password, role=role)
