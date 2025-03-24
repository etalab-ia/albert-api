import datetime as dt

import pandas as pd
import streamlit as st

from ui.backend.account import change_password, create_token, delete_token
from ui.settings import settings
from ui.frontend.header import header
from ui.backend.common import get_limits, get_models, get_tokens

header()
tokens = get_tokens()
models = get_models(api_key=st.session_state["user"].api_key)

with st.sidebar:
    if st.button(label="**:material/refresh: Refresh data**", key="refresh-sidebar-account", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

col1, col2 = st.columns(2)
with col1:
    st.metric(label="User ID", value=st.session_state["user"].name)

    with st.expander(label="Change password", icon=":material/key:"):
        current_password = st.text_input(label="Current password", type="password", key="current_password")
        new_password = st.text_input(
            label="New password",
            type="password",
            key="new_password",
            help="New password must be at least 8 characters long and contain at least one uppercase letter, one special character, and one digit.",
        )
        confirm_password = st.text_input(label="Confirm password", type="password", key="confirm_password")

        submit_change_password = st.button(
            label="Change",
            disabled=not current_password or not new_password or not confirm_password or st.session_state["user"].name == settings.master_username,
        )
        if submit_change_password:
            change_password(current_password=current_password, new_password=new_password, confirm_password=confirm_password)

with col2:
    st.metric(
        label="Expires at",
        value=pd.to_datetime(st.session_state["user"].user["expires_at"], unit="s").strftime("%d %b %Y")
        if st.session_state["user"].user["expires_at"]
        else None,
    )

st.subheader("API keys")
tokens = pd.DataFrame(
    data={
        "ID": [token["id"] for token in tokens],
        "Token": [token["token"] for token in tokens],
        "Created at": [pd.to_datetime(token["created_at"], unit="s") for token in tokens],
        "Expiration": [pd.to_datetime(token["expires_at"], unit="s") for token in tokens],
    }
)
st.dataframe(
    data=tokens.style.apply(
        lambda x: ["background-color: #f0f0f0;color: grey" if x["Expiration"] and x["Expiration"] < pd.Timestamp.now() else "" for _ in x],
        axis=1,
    ),
    use_container_width=True,
    hide_index=True,
    column_config={
        "ID": st.column_config.ListColumn(label="ID"),
        "Expiration": st.column_config.DatetimeColumn(label="Expiration", format="D MMM YYYY"),
        "Created at": st.column_config.DatetimeColumn(label="Created at", format="D MMM YYYY"),
    },
)

col1, col2 = st.columns(spec=2)
with col1:
    with st.expander(label="Create a token", icon=":material/add_circle:"):
        token_id = st.text_input(label="Token ID", placeholder="my-token", help="ID of the token to create.")
        expires_at = st.date_input(
            label="Expires at",
            min_value=dt.datetime.now(),
            max_value=dt.datetime.now() + dt.timedelta(days=settings.max_token_expiration_days),
            value=dt.datetime.now() + dt.timedelta(days=settings.max_token_expiration_days),
            help="Expiration date of the token.",
        )
        if st.button(label="Create", disabled=not token_id or st.session_state["user"].name == settings.master_username):
            create_token(token_id=token_id, expires_at=round(int(expires_at.strftime("%s"))))

with col2:
    with st.expander(label="Delete a token", icon=":material/delete_forever:"):
        token_id = st.selectbox(label="Token ID", options=tokens.ID.values)
        if st.button(label="Delete", disabled=not token_id or st.session_state["user"].name == settings.master_username, key="delete_token_button"):
            delete_token(token_id=token_id)

st.subheader("Rate limits")
limits = get_limits(models=models, role=st.session_state["user"].role)
st.dataframe(
    data=pd.DataFrame(
        data={
            "Request per minute": [limits[model]["rpm"] for model in models],
            "Request per day": [limits[model]["rpd"] for model in models],
            "Tokens per minute": [limits[model]["tpm"] for model in models],
        },
        index=models,
    ),
    use_container_width=True,
)
