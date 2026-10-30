import streamlit as st

from services.auth import current_user, get_role, sign_out


def _handle_logout():
    sign_out()


def render_sidebar():
    with st.sidebar:
        st.title("Klasterisasi dan panel regression")

        st.divider()

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
            st.link_button(
                "Lihat masukan pengguna",
                url="https://docs.google.com/spreadsheets/d/13vVQ56RuwNWsGZGAycWioF1sKDjQofXklZuWXujvpV0/edit?usp=sharing",
                icon="📋",
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
            st.link_button(
                "Kasih kita masukanmu",
                url="https://docs.google.com/forms/d/e/1FAIpQLScx0c3dJIJMMjHX8SOp4dpKDdsznHXLoLRyCW4OSvJnz2vXCg/viewform?usp=dialog",
                icon="📢",
            )

        st.divider()

        user = current_user()
        if user is not None:
            st.caption(f"Masuk sebagai {user.email}")
        st.button("Logout", icon="🚪", on_click=_handle_logout)

        st.divider()

        st.caption("© 2026")