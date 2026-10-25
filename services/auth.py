"""Supabase authentication helpers for the Streamlit app."""

import os

import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()  # reads .env from the project root (where you run `streamlit run`)

MIN_PASSWORD_LENGTH = 6  # Supabase's default minimum


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
    return True, ""


def sign_up(email: str, password: str) -> tuple[bool, str, bool]:
    """Returns (ok, message, logged_in).

    If "Confirm email" is enabled in Supabase, no session is returned and the
    user must confirm via email before logging in.
    """
    try:
        res = get_client().auth.sign_up({"email": email, "password": password})
    except Exception as exc:
        return False, _error_message(exc), False

    if res.session is not None and res.user is not None:
        st.session_state["user"] = res.user
        return True, "Account created.", True

    return True, "Account created. Check your email to confirm it, then log in.", False


def sign_out() -> None:
    """Sign out of Supabase and wipe this browser session's state."""
    try:
        get_client().auth.sign_out()
    except Exception:
        pass  # still clear local state even if the network call fails
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def require_login() -> None:
    """Defense in depth: call at the top of every protected page.

    st.navigation already hides these pages from logged-out users; this guard
    covers someone running a page file directly.
    """
    if not is_authenticated():
        st.warning("Please log in to view this page.")
        st.stop()