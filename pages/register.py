import streamlit as st

from services.auth import MIN_PASSWORD_LENGTH, sign_up

st.title("Registrasi")

with st.form("register_form"):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    confirm = st.text_input("Konfirmasi Password", type="password")
    submitted = st.form_submit_button("Buat akun")

if submitted:
    if not email or not password:
        st.error("Isi seluruh formulir")
    elif len(password) < MIN_PASSWORD_LENGTH:
        st.error(f"Password harus lebih dari {MIN_PASSWORD_LENGTH} huruf.")
    elif password != confirm:
        st.error("Password berbeda.")
    else:
        ok, message, logged_in = sign_up(email.strip(), password)
        if not ok:
            st.error(message)
        elif logged_in:
            st.rerun()
        else:
            st.success(message)

st.page_link("pages/login.py", label="Sudah mempunyai akun? Login sekarang")