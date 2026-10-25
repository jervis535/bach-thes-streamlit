import streamlit as st

from components.sidebar import render_sidebar
from services.auth import init_auth, is_authenticated

st.set_page_config(
    page_title="My App",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_auth()

# Only the pages a user is allowed to see are registered. Anything not in this
# list can't be navigated to, even by typing its URL.
if is_authenticated():
    pages = [
        st.Page("pages/clustering.py", title="Clustering", icon="📊", default=True),
        st.Page("pages/panel_regression.py", title="Panel Regression", icon="📈"),
        st.Page("pages/instructions.py", title="Instructions", icon="📋"),
    ]
else:
    pages = [
        st.Page("pages/login.py", title="Login", icon="🔐", default=True),
        st.Page("pages/register.py", title="Register", icon="📝"),
    ]

# Hide the built-in nav; the custom sidebar below replaces it for logged-in users.
page = st.navigation(pages, position="hidden")

if is_authenticated():
    render_sidebar()

page.run()