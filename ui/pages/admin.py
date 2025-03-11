import re
import time
from typing import Optional

import pandas as pd
import requests
import streamlit as st

from utils.common import clear_cache, get_models, header, settings
from utils.variables import MODEL_TYPE_LANGUAGE


def get_roles(return_dataframe: bool = False):
    response = requests.get(url=f"{settings.api_url}/roles", headers={"Authorization": f"Bearer {settings.api_key}"})
    data = response.json()["data"]

    return data


def get_users():
    response = requests.get(url=f"{settings.api_url}/users", headers={"Authorization": f"Bearer {settings.api_key}"})
    data = response.json()["data"]

    return data


def create_role(role_id: str, default: bool, admin: bool):
    response = requests.post(
        url=f"{settings.api_url}/roles",
        headers={"Authorization": f"Bearer {settings.api_key}"},
        json={"role": role_id, "default": default, "admin": admin},
    )
    if response.status_code == 201:
        st.toast("Role created", icon="✅")
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast("Role creation failed", icon="❌")


def delete_role(role_id: str):
    response = requests.delete(url=f"{settings.api_url}/roles/{role_id}", headers={"Authorization": f"Bearer {settings.api_key}"})
    if response.status_code == 204:
        st.toast("Role deleted", icon="✅")
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast("Role deletion failed", icon="❌")


def update_limits(role_id: str, limits: list):
    response = requests.patch(
        url=f"{settings.api_url}/roles/{role_id}",
        json={"limits": limits},
        headers={"Authorization": f"Bearer {settings.api_key}"},
    )
    if response.status_code == 201:
        st.toast("Limits updated", icon="✅")
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast("Limits update failed", icon="❌")


def update_role(role_id: str, role: Optional[str] = None, default: Optional[bool] = None, admin: Optional[bool] = None):
    response = requests.patch(
        url=f"{settings.api_url}/roles/{role_id}",
        json={"role": role, "default": default, "admin": admin},
        headers={"Authorization": f"Bearer {settings.api_key}"},
    )
    if response.status_code == 201:
        st.toast("Role updated", icon="✅")
        time.sleep(0.5)
        st.rerun()
    else:
        st.toast("Role update failed", icon="❌")


header()

if not st.session_state["user"]["role"]["admin"]:
    st.info("Access denied")
    st.stop()

users = get_users()
roles = get_roles()
models = get_models(type=MODEL_TYPE_LANGUAGE)


with st.sidebar:
    if st.button(label="**:material/refresh: Refresh data**", key="refresh-sidebar-account", use_container_width=True):
        clear_cache()

st.subheader("Roles")

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

if st.button(label="Update", key="update_roles_button"):
    for index, row in edited_roles.iterrows():
        new_role = row["ID"] if row["ID"] != initial_roles.loc[index, "ID"] else None
        new_default = row["Default"] if row["Default"] != initial_roles.loc[index, "Default"] else None
        new_admin = row["Admin"] if row["Admin"] != initial_roles.loc[index, "Admin"] else None
        update_role(role_id=row["ID"], role=new_role, default=new_default, admin=new_admin)


col1, col2 = st.columns(spec=2)

with col1:
    with st.expander(label="Create a role", icon=":material/add_circle:"):
        role_id = st.text_input(label="Role ID", placeholder="my-role", help="ID of the role to create.")
        _col1, _col2 = st.columns(spec=2)
        with _col1:
            default = st.toggle(label="Default", value=False)
        with _col2:
            admin = st.toggle(
                label="Admin",
                help="Admin rights: access to all models with no rate limits, manage roles, users and public collections.",
                value=False,
            )

        submit_create = st.button(label="Create", disabled=not role_id)
        if submit_create:
            create_role(role_id=role_id, default=default, admin=admin)
            clear_cache()

with col2:
    with st.expander(label="Delete a role", icon=":material/delete_forever:"):
        role_id = st.selectbox(label="Role ID", options=[role["id"] for role in roles])
        submit_delete = st.button(label="Delete", disabled=not role_id, key="delete_role_button")
        if submit_delete:
            delete_role(role_id=role_id)

if selected_role := st.selectbox(
    label="**Rate limits**", options=[role["id"] for role in roles], index=[role["default"] for role in roles].index(True)
):
    limits = [role["limits"] for role in roles if selected_role in role["id"]][0]

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

    if st.button(label="Update", key="update_limits_button"):  # , disabled=not edited_limits.equals(initial_limits))
        edited_limits = [
            {
                "model_regex": f"^{row["Model"]}$",
                "tpm": row["Tokens per minute"],
                "rpm": row["Request per minute"],
                "rpd": row["Request per day"],
            }
            for index, row in edited_limits.iterrows()
        ]
        update_limits(role_id=selected_role, limits=edited_limits)


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
