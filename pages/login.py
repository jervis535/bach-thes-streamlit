import streamlit as st

from services.auth import sign_in

st.title("Login")

with st.form("login_form"):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    submitted = st.form_submit_button("Login")

if submitted:
    if not email or not password:
        st.error("Masukkan email dan password")
    else:
        ok, error = sign_in(email.strip(), password)
        if ok:
            st.rerun()
        else:
            st.error(error)

st.page_link("pages/register.py", label="Tidak ada akun? Daftar sekarang")