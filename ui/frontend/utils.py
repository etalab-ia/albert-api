import streamlit as st
from streamlit_extras.stylable_container import stylable_container


def pagination(key: str, data: list, per_page: int = 10):
    _, left, center, right, _ = st.columns(spec=[10, 1.5, 1.5, 1.5, 10])
    with left:
        if st.button(
            label="**:material/keyboard_double_arrow_left:**",
            key=f"pagination-{key}-previous",
            disabled=st.session_state.get(f"{key}-offset", 0) == 0,
            use_container_width=True,
        ):
            st.session_state[key] = max(0, st.session_state.get(key, 0) - per_page)
            st.rerun()

    with center:
        st.button(label=str(round(st.session_state.get(f"{key}-offset", 0) / per_page)), key=f"pagination-{key}-offset", use_container_width=True)

    with right:
        with stylable_container(key="Header", css_styles="button{float: right;}"):
            if st.button(
                label="**:material/keyboard_double_arrow_right:**",
                key=f"pagination-{key}-next",
                disabled=len(data) < per_page,
                use_container_width=True,
            ):
                st.session_state[key] = st.session_state.get(key, 0) + per_page
                st.rerun()
