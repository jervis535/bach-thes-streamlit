import streamlit as st


def render_sidebar():
    with st.sidebar:
        st.title("My App")
        st.caption("Application workspace")

        st.divider()

        st.page_link("app.py", label="Home", icon="🏠")
        st.page_link(
            "pages/dashboard.py",
            label="Dashboard",
            icon="📊",
        )
        st.page_link(
            "pages/settings.py",
            label="Settings",
            icon="⚙️",
        )

        st.divider()

        st.caption("© 2026 My App")