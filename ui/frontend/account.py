import datetime as dt

import pandas as pd
import streamlit as st

from ui.backend.account import change_password, create_token, delete_token
from ui.backend.common import get_limits, get_models, get_tokens, get_usage
from ui.frontend.header import header
from ui.frontend.utils import pagination
from ui.settings import settings

header()
models = get_models() + ["web-search"]

with st.sidebar:
    if st.button(label="**:material/refresh: Refresh data**", key="refresh-sidebar-account", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


st.metric(label="User ID", value=st.session_state["user"].name, border=True)

with st.expander(label="Change password", icon=":material/key:"):
    current_password = st.text_input(label="Current password", type="password", key="current_password", icon=":material/lock:")
    new_password = st.text_input(
        label="New password",
        type="password",
        key="new_password",
        help="New password must be at least 8 characters long and contain at least one uppercase letter, one special character, and one digit.",
        icon=":material/lock:",
    )
    confirm_password = st.text_input(label="Confirm password", type="password", key="confirm_password", icon=":material/lock:")

    submit_change_password = st.button(
        label="Change",
        disabled=not current_password or not new_password or not confirm_password or st.session_state["user"].name == settings.auth.master_username,
    )
    if submit_change_password:
        change_password(current_password=current_password, new_password=new_password, confirm_password=confirm_password)


col1, col2 = st.columns(spec=2)
with col1:
    st.metric(
        label="Account expiration",
        value=pd.to_datetime(st.session_state["user"].user["expires_at"], unit="s").strftime("%d %b %Y")
        if st.session_state["user"].user["expires_at"]
        else None,
        border=False,
    )
with col2:
    st.metric(
        label="Budget",
        value=round(st.session_state["user"].user["budget"], 4) if st.session_state["user"].user["budget"] else None,
        border=False,
    )

st.subheader("My Usage")

# Date filters
col1, col2 = st.columns(2)
with col1:
    date_from = st.date_input(label="From date", value=dt.datetime.now() - dt.timedelta(days=30), key="usage_date_from")
with col2:
    date_to = st.date_input(label="To date", value=dt.datetime.now().date(), min_value=date_from, key="usage_date_to")

# Convert dates to timestamps
date_from_timestamp = int(dt.datetime.combine(date_from, dt.time.min).timestamp())
date_to_timestamp = int(dt.datetime.combine(date_to, dt.time.max).timestamp())

# Initialize pagination state
usage_key = "usage_pagination"
if usage_key not in st.session_state:
    st.session_state[usage_key] = 0

# Reset pagination when date filters change
date_key = f"{date_from_timestamp}_{date_to_timestamp}"
if f"{usage_key}_date_key" not in st.session_state or st.session_state[f"{usage_key}_date_key"] != date_key:
    st.session_state[usage_key] = 0
    st.session_state[f"{usage_key}_date_key"] = date_key

# Calculate page number from offset
per_page = 25
current_offset = st.session_state[usage_key]
current_page = (current_offset // per_page) + 1

usage_response = get_usage(
    limit=per_page,
    page=current_page,
    order_by="datetime",
    order_direction="desc",
    date_from=date_from_timestamp,
    date_to=date_to_timestamp,
)

usage_data = usage_response.get("data", [])
total_requests = usage_response.get("total_requests", 0)
total_albert_coins = usage_response.get("total_albert_coins", 0.0)
total_tokens = usage_response.get("total_tokens", 0)
total_co2 = usage_response.get("total_co2", 0.0)

# Pagination information
current_page = usage_response.get("page", 1)
total_pages = usage_response.get("total_pages", 1)
has_more = usage_response.get("has_more", False)
limit = usage_response.get("limit", 50)

if usage_data:
    # Summary statistics from API calculations
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="Total Requests",
            value=total_requests,
            border=True,
        )
    with col2:
        st.metric(
            label="Total Albert coins",
            value=f"{total_albert_coins:.4f}",
            border=True,
        )
    with col3:
        st.metric(
            label="Total Tokens",
            value=f"{total_tokens:,}",
            border=True,
        )
    with col4:
        st.metric(
            label="Total CO2 (g)",
            value=f"{total_co2:.4f}",
            border=True,
        )
    usage_df = pd.DataFrame(
        data={
            "Datetime": [pd.to_datetime(record["datetime"], unit="s") for record in usage_data],
            "Endpoint": [record["endpoint"] for record in usage_data],
            "Model": [record["model"] for record in usage_data],
            # "Request Model": [record["request_model"] for record in usage_data],
            # "Method": [record["method"] for record in usage_data],
            # "Duration (s)": [record["duration"] for record in usage_data]
            # "Time to First Token (s)": [record["time_to_first_token"] for record in usage_data],
            "Tokens": [f"{record["prompt_tokens"]} → {record["completion_tokens"]}" for record in usage_data],
            # "Completion Tokens": [record["completion_tokens"] for record in usage_data],
            # "Total Tokens": [record["total_tokens"] for record in usage_data],
            "Cost": [record["cost"] for record in usage_data],
            # "Status": [record["status"] for record in usage_data],
            # "kWh Min": [record["kwh_min"] for record in usage_data],
            # "kWh Max": [record["kwh_max"] for record in usage_data],
            # "CO2eq Min (kg)": [record["kgco2eq_min"] for record in usage_data],
            # "CO2eq Max (kg)": [record["kgco2eq_max"] for record in usage_data],
        }
    )

    st.dataframe(
        data=usage_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Datetime": st.column_config.DatetimeColumn(label="Datetime", format="DD/MM/YY HH:mm"),
            # "Duration (s)": st.column_config.NumberColumn(label="Duration (s)", format="%.3f"),
            # "Time to First Token (s)": st.column_config.NumberColumn(label="Time to First Token (s)", format="%.3f"),
            "Cost": st.column_config.NumberColumn(label="Cost", format="%.6f"),
            # "kWh Min": st.column_config.NumberColumn(label="kWh Min", format="%.6f"),
            # "kWh Max": st.column_config.NumberColumn(label="kWh Max", format="%.6f"),
            # "CO2eq Min (kg)": st.column_config.NumberColumn(label="CO2eq Min (kg)", format="%.6f"),
            # "CO2eq Max (kg)": st.column_config.NumberColumn(label="CO2eq Max (kg)", format="%.6f"),
        },
    )

    # Add pagination controls
    if total_pages > 1 or has_more:
        pagination(key=usage_key, data=usage_data, per_page=per_page)


else:
    st.info("No usage data available.")


st.subheader("API keys")
key, per_page = "token", 10
tokens = get_tokens(offset=st.session_state.get(f"{key}-offset", 0), limit=per_page)
st.dataframe(
    data=pd.DataFrame(
        data={
            "ID": [token["id"] for token in tokens],
            "Name": [token["name"] for token in tokens],
            "Token": [token["token"] for token in tokens],
            "Created at": [pd.to_datetime(token["created_at"], unit="s") for token in tokens],
            "Expiration": [pd.to_datetime(token["expires_at"], unit="s") for token in tokens],
        }
    ).style.apply(
        lambda x: [
            "background-color: #f0f0f0;color: grey"
            if (x["Expiration"] and x["Expiration"] < pd.Timestamp.now()) or x["ID"] == st.session_state["user"].api_key_id
            else ""
            for _ in x
        ],
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
pagination(key=key, data=tokens, per_page=per_page)

col1, col2 = st.columns(spec=2)
with col1:
    with st.expander(label="Create an API key", icon=":material/add_circle:"):
        token_name = st.text_input(label="API key name", placeholder="Enter a name for your API key", help="Please refresh data after creating an API key.", icon=":material/key:")  # fmt: off
        max_value = dt.datetime.now() + dt.timedelta(days=settings.auth.max_token_expiration_days) if settings.auth.max_token_expiration_days else None  # fmt: off
        expires_at = st.date_input(label="Expires at",  min_value=dt.datetime.now(), max_value=max_value, value=max_value, help="Expiration date of the API key.")  # fmt: off
        if st.button(label="Create", disabled=not token_name or st.session_state["user"].name == settings.auth.master_username):
            create_token(name=token_name, expires_at=round(int(expires_at.strftime("%s"))))

with col2:
    with st.expander(label="Delete an API key", icon=":material/delete_forever:"):
        token_name = st.selectbox(
            label="API key ID",
            options=[f"{token["name"]} ({token["id"]})" for token in tokens],
            help="Playground API key cannot be deleted.",
        )
        token_id = [token["id"] for token in tokens if f"{token["name"]} ({token["id"]})" == token_name][0] if token_name else None
        if st.button(label="Delete", disabled=not token_id or st.session_state["user"].name == settings.auth.master_username or token_name == "playground", key="delete_token_button"):  # fmt: off
            delete_token(token_id=token_id)

st.subheader("Rate limits")
limits = get_limits(models=models, role=st.session_state["user"].role)
st.dataframe(
    data=pd.DataFrame(
        data={
            "Request per minute": [limits[model]["rpm"] if limits[model]["rpm"] is not None else "Unlimited" for model in models],
            "Request per day": [limits[model]["rpd"] if limits[model]["rpd"] is not None else "Unlimited" for model in models],
            "Tokens per minute": [limits[model]["tpm"] if limits[model]["tpm"] is not None else "Unlimited" for model in models],
            "Tokens per day": [limits[model]["tpd"] if limits[model]["tpd"] is not None else "Unlimited" for model in models],
        },
        index=models,
    ),
    use_container_width=True,
)
st.info("**Limits are common to all your API keys**, contact support to increase your rate limits.")
