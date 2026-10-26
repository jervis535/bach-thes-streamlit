import streamlit as st

from services.auth import current_user, get_role, sign_out


def _handle_logout():
    sign_out()


def render_sidebar():
    with st.sidebar:
        st.title("Klasterisasi dan panel regression")

        st.divider()

        # page_link only works for pages registered in app.py, so the links
        # here must match the pages each role gets there.
        if get_role() == "admin":
            st.page_link(
                "pages/use_count.py",
                label="Jumlah penggunaan layanan",
                icon="📊",
            )
            st.page_link(
                "pages/user_count.py",
                label="Jumlah registrasi pengguna",
                icon="👥",
            )
        else:
            st.page_link(
                "pages/clustering.py",
                label="Klasterisasi",
                icon="📊",
            )
            st.page_link(
                "pages/panel_regression.py",
                label="Panel Regression",
                icon="📈",
            )
            st.page_link(
                "pages/instructions.py",
                label="Instruksi",
                icon="📋",
            )

        st.divider()

        user = current_user()
        if user is not None:
            st.caption(f"Masuk sebagai {user.email}")
        st.button("Log out", icon="🚪", on_click=_handle_logout)

        st.divider()

        st.caption("© 2026")