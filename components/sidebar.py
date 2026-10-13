import streamlit as st


def render_sidebar():
    with st.sidebar:
        st.title("My App")
        st.caption("Application workspace")

        st.divider()

        st.page_link(
            "pages/clustering.py", 
            label="Clustering", 
            icon="📊"
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

        st.caption("© 2026 My App")