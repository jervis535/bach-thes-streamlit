import streamlit as st

from components.sidebar import render_sidebar
from services.auth import ALLOWED_ROLES, get_role, init_auth, is_authenticated

st.set_page_config(
    page_title="My App",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_auth()

authenticated = is_authenticated()
role = get_role() if authenticated else None

# Only the pages a visitor is allowed to see are registered. Anything not in
# this list can't be navigated to, even by typing its URL.
if role in ALLOWED_ROLES:
    pages = [
        st.Page("pages/clustering.py", title="Clustering", icon="📊", default=True),
        st.Page("pages/panel_regression.py", title="Panel Regression", icon="📈"),
        st.Page("pages/instructions.py", title="Instructions", icon="📋"),
    ]
elif role == "admin":
    pages = [
        st.Page(
            "pages/use_count.py",
            title="Usage statistics",
            icon="📊",
            default=True,
        ),
        st.Page("pages/user_count.py", 
            title="Registered users", 
            icon="👥"
        ),
    ]
elif authenticated:
    # Logged in, but the role isn't allowed (or has no profile row yet).
    pages = [
        st.Page("pages/no_access.py", title="No access", icon="🚫", default=True),
    ]
else:
    pages = [
        st.Page("pages/login.py", title="Login", icon="🔐", default=True),
        st.Page("pages/register.py", title="Register", icon="📝"),
    ]

# Hide the built-in nav; the custom sidebar below replaces it once logged in.
page = st.navigation(pages, position="hidden")

if role in ALLOWED_ROLES or role == "admin":
    render_sidebar()

page.run()