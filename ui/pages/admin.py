import streamlit as st

from utils.common import header

header()

st.write(st.session_state["user"])
if not st.session_state["user"]["role"]["admin"]:
    st.info("Access denied")
    st.stop()

st.title("Admin")
