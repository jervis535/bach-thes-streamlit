import streamlit as st

from services.auth import current_user, sign_out


def _handle_logout():
    sign_out()


def render_sidebar():
    with st.sidebar:
        st.title("My App")
        st.caption("My app")

        st.divider()

        st.page_link(
            "pages/clustering.py",
            label="Clustering",
            icon="📊",
        )
        st.page_link(
            "pages/panel_regression.py",
            label="Panel Regression",
            icon="📈",
        )
        st.page_link(
            "pages/instructions.py",
            label="Instructions",
            icon="📋",
        )

        st.divider()

        user = current_user()
        if user is not None:
            st.caption(f"Signed in as {user.email}")
        st.button("Log out", icon="🚪", on_click=_handle_logout)

        st.divider()

        st.caption("© 2026 My App")