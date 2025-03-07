import datetime as dt

import pandas as pd
import streamlit as st

from utils.account import change_password, create_token, delete_token
from utils.common import get_tokens, header, settings

header()
tokens = get_tokens()

with st.sidebar:
    if st.button(label="**:material/refresh: Refresh data**", key="refresh-sidebar-account", use_container_width=True):
        st.cache_data.clear()

col1, col2 = st.columns(2)
with col1:
    st.metric(label="User ID", value=st.session_state["user"]["id"])

    with st.expander(label="Change password", icon=":material/key:"):
        current_password = st.text_input(label="Current password", type="password", key="current_password")
        new_password = st.text_input(
            label="New password",
            type="password",
            key="new_password",
            help="New password must be at least 8 characters long and contain at least one uppercase letter, one special character, and one digit.",
        )
        confirm_password = st.text_input(label="Confirm password", type="password", key="confirm_password")

        submit_change_password = st.button(label="Change", disabled=not current_password or not new_password or not confirm_password)
        if submit_change_password:
            change_password(current_password=current_password, new_password=new_password, confirm_password=confirm_password)

# TODO: add expires at
# with col2:
#     st.metric(label="Expires at", value=pd.to_datetime(st.session_state["user"]["expires_at"], unit="s"))


st.divider()
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
        if st.button(label="Create", disabled=not token_id):
            create_token(token_id=token_id, expires_at=round(int(expires_at.strftime("%s"))))

with col2:
    with st.expander(label="Delete a token", icon=":material/delete_forever:"):
        token_id = st.selectbox(label="Token ID", options=tokens.ID.values)
        if st.button(label="Delete", disabled=not token_id, key="delete_token_button"):
            delete_token(token_id=token_id)
