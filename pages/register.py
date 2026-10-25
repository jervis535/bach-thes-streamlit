import streamlit as st

from services.auth import MIN_PASSWORD_LENGTH, sign_up

st.title("📝 Register")

with st.form("register_form"):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    confirm = st.text_input("Confirm password", type="password")
    submitted = st.form_submit_button("Create account")

if submitted:
    if not email or not password:
        st.error("Please fill in all fields.")
    elif len(password) < MIN_PASSWORD_LENGTH:
        st.error(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    elif password != confirm:
        st.error("Passwords do not match.")
    else:
        ok, message, logged_in = sign_up(email.strip(), password)
        if not ok:
            st.error(message)
        elif logged_in:
            st.rerun()
        else:
            st.success(message)

st.page_link("pages/login.py", label="Already have an account? Log in")