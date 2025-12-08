"""Authentication utilities for Streamlit."""

import streamlit as st
from typing import Any


def is_logged_in() -> bool:
    """Check if user is logged in.
    
    Returns:
        True if user has valid token in session
    """
    return bool(st.session_state.get("auth_token"))


def get_current_user() -> dict[str, Any] | None:
    """Get current logged in user.
    
    Returns:
        User info dict or None
    """
    return st.session_state.get("auth_user")


def get_auth_token() -> str | None:
    """Get current auth token.
    
    Returns:
        JWT token or None
    """
    return st.session_state.get("auth_token")


def set_auth(token: str, user: dict[str, Any]) -> None:
    """Set authentication state.
    
    Args:
        token: JWT access token
        user: User info dict
    """
    st.session_state.auth_token = token
    st.session_state.auth_user = user


def logout() -> None:
    """Clear authentication state."""
    st.session_state.pop("auth_token", None)
    st.session_state.pop("auth_user", None)


def require_login() -> bool:
    """Check login and redirect if not logged in.
    
    Returns:
        True if logged in, False otherwise (shows warning)
    """
    if not is_logged_in():
        st.warning("请先登录")
        st.page_link("pages/1_🔐_Login.py", label="前往登录", icon="🔐")
        return False
    return True
