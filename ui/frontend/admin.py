import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from ui.backend.admin import create_role, create_user, delete_role, delete_user, refresh_playground_api_key, update_role, update_user
from ui.frontend.header import header
from ui.frontend.utils import (
    input_new_role_limits,
    input_new_role_name,
    input_new_role_permissions,
    input_new_user_expires_at,
    input_new_user_name,
    input_new_user_password,
    input_new_user_role_id,
    input_new_user_budget,
    ressources_selector,
)
from ui.variables import ADMIN_PERMISSIONS

header()
if not all(perm in st.session_state["user"].role["permissions"] for perm in ADMIN_PERMISSIONS):
    st.info("Access denied.")
    st.stop()

# Roles
with st.expander(
    label="Roles",
    expanded=not st.session_state.get("new_role", False)
    and not st.session_state.get("update_role", False)
    and not st.session_state.get("new_user", False)
    and not st.session_state.get("update_user", False),
):
    roles, selected_role = ressources_selector(ressource="role")
    st.session_state["no_roles"] = True if roles == [] else False
    with stylable_container(key="Header", css_styles="button{float: right;}"):
        if st.button(
            label="**:material/delete_forever: Delete**",
            key="delete_role_button",
            disabled=st.session_state.get("new_role", False) or st.session_state["no_roles"],
        ):
            delete_role(role=selected_role["id"])

new_role_name = input_new_role_name(selected_role=selected_role)
new_role_permissions = input_new_role_permissions(selected_role=selected_role)
new_role_limits = input_new_role_limits(selected_role=selected_role)

if st.session_state.get("new_role", False):
    with stylable_container(key="Header", css_styles="button{float: right;}"):
        if st.button(label="**Create**", key="validate_create_role_button"):
            create_role(name=new_role_name, permissions=new_role_permissions, limits=new_role_limits)

if st.session_state.get("update_role", False):
    with stylable_container(key="Header", css_styles="button{float: right;}"):
        if st.button(label="**Update**", key="validate_update_role_button"):
            update_role(role=selected_role["id"], name=new_role_name, permissions=new_role_permissions, limits=new_role_limits)

with st.sidebar:
    st.subheader("**Roles**")
    col1, col2 = st.columns(spec=2)
    with col1:
        st.button(
            label="**:material/add: Create**",
            key="create_new_role",
            on_click=lambda: setattr(st.session_state, "new_role", not st.session_state.get("new_role", False))
            and setattr(st.session_state, "update_role", False),
            use_container_width=True,
            type="primary" if st.session_state.get("new_role", False) else "secondary",
            disabled=st.session_state.get("update_role", False),
        )
    with col2:
        st.button(
            label="**:material/update: Update**",
            key="update_role_button",
            on_click=lambda: setattr(st.session_state, "update_role", not st.session_state.get("update_role", False))
            and setattr(st.session_state, "new_role", False),
            use_container_width=True,
            type="primary" if st.session_state.get("update_role", False) else "secondary",
            disabled=st.session_state.get("new_role", False) or st.session_state["no_roles"],
        )

# Users
if not roles or st.session_state.get("new_role", False) or st.session_state.get("update_role", False):
    st.stop()

st.markdown(body=f"#### Users of the *{"new" if st.session_state.get("new_role", False) else selected_role["name"]}* role")
with st.expander(label="Users", expanded=not st.session_state.get("new_user", False)):
    users, selected_user = ressources_selector(ressource="user", filter=selected_role["id"])
    st.session_state["no_users_in_selected_role"] = True if users == [] else False
    col1, col2 = st.columns(spec=2)
    with col1:
        if st.button(
            label="**:material/key: Refresh playground key**",
            key="refresh_playground_user_api_key_button",
            # use_container_width=True,
            disabled=st.session_state.get("new_user", False) or st.session_state["no_users_in_selected_role"],
        ):
            refresh_playground_api_key(user=selected_user.get("id"))

        with col2:
            with stylable_container(key="Header", css_styles="button{float: right;}"):
                if st.button(
                    label="**:material/delete_forever: Delete**",
                    key="delete_user_button",
                    # use_container_width=True,
                    disabled=st.session_state.get("new_user", False) or st.session_state["no_users_in_selected_role"],
                ):
                    delete_user(user=selected_user.get("id"))


new_user_name = input_new_user_name(selected_user=selected_user)
new_user_password = input_new_user_password()
new_user_role_id = input_new_user_role_id(selected_role=selected_role, roles=roles)
new_user_budget = input_new_user_budget(selected_user=selected_user)
new_user_expires_at = input_new_user_expires_at(selected_user=selected_user)


if st.session_state.get("new_user", False):
    with stylable_container(key="Header", css_styles="button{float: right;}"):
        if st.button(label="**Create**", key="validate_create_user_button"):
            create_user(name=new_user_name, password=new_user_password, budget=new_user_budget, role=new_user_role_id, expires_at=new_user_expires_at)

if st.session_state.get("update_user", False):
    with stylable_container(key="Header", css_styles="button{float: right;}"):
        if st.button(label="**Update**", key="validate_update_user_button"):
            update_user(
                user=selected_user["id"],
                name=new_user_name,
                password=new_user_password,
                budget=new_user_budget,
                role=new_user_role_id,
                expires_at=new_user_expires_at,
            )

with st.sidebar:
    st.subheader("**Users**")
    col1, col2 = st.columns(spec=2)
    with col1:
        st.button(
            label="**:material/add: Create**",
            key="create_user_button",
            on_click=lambda: setattr(st.session_state, "new_user", not st.session_state.get("new_user", False))
            and setattr(st.session_state, "update_user", False),
            use_container_width=True,
            type="primary" if st.session_state.get("new_user", False) else "secondary",
            disabled=st.session_state.get("update_user", False),
        )
    with col2:
        st.button(
            label="**:material/update: Update**",
            key="update_user_button",
            on_click=lambda: setattr(st.session_state, "update_user", not st.session_state.get("update_user", False))
            and setattr(st.session_state, "new_user", False),
            use_container_width=True,
            type="primary" if st.session_state.get("update_user", False) else "secondary",
            disabled=st.session_state.get("new_user", False) or st.session_state["no_users_in_selected_role"],
        )
