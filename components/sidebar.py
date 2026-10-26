import streamlit as st

from services.auth import current_user, get_role, sign_out


def _handle_logout():
    sign_out()


def render_sidebar():
    with st.sidebar:
        st.title("My App")
        st.caption("My app")

        st.divider()

        # page_link only works for pages registered in app.py, so the links
        # here must match the pages each role gets there.
        if get_role() == "admin":
            st.page_link(
                "pages/use_count.py",
                label="Usage statistics",
                icon="📊",
            )
            st.page_link(
                "pages/user_count.py",
                label="Registered users",
                icon="👥",
            )
        else:
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