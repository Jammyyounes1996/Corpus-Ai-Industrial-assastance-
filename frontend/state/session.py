import streamlit as st


def init_session_state() -> None:
    """Initialize default session state values."""
    defaults = {
        "current_chat_id": None,
        "current_project_id": None,
        "model_provider": "ollama",
        "model_name": "gemma4:latest",
        "theme": "light",
        "backend_connected": False,
        "sidebar_open": True,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_session_value(key: str, default=None):
    """Retrieve a value from session state.

    Args:
        key: The session state key.
        default: Default value if key is not found.

    Returns:
        The session state value or the default.
    """
    return st.session_state.get(key, default)


def set_session_value(key: str, value) -> None:
    """Set a value in session state.

    Args:
        key: The session state key.
        value: The value to set.
    """
    st.session_state[key] = value
