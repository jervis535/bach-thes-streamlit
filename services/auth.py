"""Supabase authentication and role helpers for the Streamlit app."""

import os

import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()  # reads .env from the project root (where you run `streamlit run`)

MIN_PASSWORD_LENGTH = 6  # Supabase's default minimum

# Roles allowed to open the app's protected pages. To let admins in too,
# change this to {"user", "admin"}.
ALLOWED_ROLES = {"user"}


def get_client() -> Client:
    """Return this browser session's Supabase client.

    Stored in st.session_state (NOT st.cache_resource) because the client holds
    the logged-in user's tokens. A cached/global client would be shared by
    every visitor and leak one user's session to another.
    """
    if "supabase" not in st.session_state:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            st.error(
                "Missing SUPABASE_URL or SUPABASE_KEY. "
                "Copy .env.example to .env and fill in your values."
            )
            st.stop()
        st.session_state["supabase"] = create_client(url, key)
    return st.session_state["supabase"]


def init_auth() -> None:
    """Call once per run from the entrypoint."""
    get_client()
    st.session_state.setdefault("user", None)


def is_authenticated() -> bool:
    return st.session_state.get("user") is not None


def current_user():
    return st.session_state.get("user")


def get_role() -> str | None:
    """The logged-in user's role from public.profiles, or None.

    Cached in session state after the first successful lookup, so a role
    change in the database takes effect on the user's next login.
    """
    user = current_user()
    if user is None:
        return None

    cached = st.session_state.get("role")
    if cached is not None:
        return cached

    try:
        res = (
            get_client()
            .table("profiles")
            .select("role")
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )
    except Exception:
        return None

    if not res.data:
        return None  # no profile row: treated as no access

    st.session_state["role"] = res.data[0]["role"]
    return st.session_state["role"]


def has_access() -> bool:
    """True if the logged-in user's role may use the protected pages."""
    return is_authenticated() and get_role() in ALLOWED_ROLES


def is_admin() -> bool:
    """True if the logged-in user's role is "admin"."""
    return is_authenticated() and get_role() == "admin"


def _error_message(exc: Exception) -> str:
    return getattr(exc, "message", None) or str(exc)


def sign_in(email: str, password: str) -> tuple[bool, str]:
    """Returns (ok, error_message)."""
    try:
        res = get_client().auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except Exception as exc:
        return False, _error_message(exc)

    st.session_state["user"] = res.user
    st.session_state.pop("role", None)  # always re-read the role on login
    return True, ""


def sign_up(email: str, password: str) -> tuple[bool, str, bool]:
    """Returns (ok, message, logged_in).

    New accounts get the "user" role from the database trigger in
    supabase_setup.sql, never from client code, so users can't choose their
    own role.

    If "Confirm email" is enabled in Supabase, no session is returned and the
    user must confirm via email before logging in.
    """
    try:
        res = get_client().auth.sign_up({"email": email, "password": password})
    except Exception as exc:
        return False, _error_message(exc), False

    if res.session is not None and res.user is not None:
        st.session_state["user"] = res.user
        st.session_state.pop("role", None)
        return True, "Account created.", True

    return True, "Akun berhasil dibuat silakan periksa email", False


def sign_out() -> None:
    """Sign out of Supabase and wipe this browser session's state."""
    try:
        get_client().auth.sign_out()
    except Exception:
        pass  # still clear local state even if the network call fails
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def require_login() -> None:
    """Stop the page unless someone is logged in."""
    if not is_authenticated():
        st.warning("Please log in to view this page.")
        st.stop()


def require_role() -> None:
    """Defense in depth: call at the top of every protected page.

    st.navigation already hides these pages from users without access; this
    guard covers someone running a page file directly.
    """
    require_login()
    if not has_access():
        st.error("You don't have permission to view this page.")
        st.stop()


def require_admin() -> None:
    """Call at the top of every admin page.

    app.py only registers admin pages for admins; this guard covers someone
    running a page file directly. The data itself is protected separately by
    the admin checks inside the database functions (admin_setup.sql).
    """
    require_login()
    if not is_admin():
        st.error("This page is for administrators only.")
        st.stop()