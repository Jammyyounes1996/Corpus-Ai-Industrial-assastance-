import streamlit as st


def render_status_badge(status: str) -> None:
    """Render a colored status indicator for file indexing status.

    Args:
        status: One of "indexed", "processing", "pending", "failed".
    """
    status_colors = {
        "indexed": ("✅", "green"),
        "processing": ("⏳", "orange"),
        "pending": ("⚪", "gray"),
        "failed": ("❌", "red"),
    }

    icon, color = status_colors.get(status, ("❓", "gray"))
    label = status.replace("_", " ").title()

    styled = (
        f'<span style="'
        f"background-color: {color}20; "
        f"color: {color}; "
        f"padding: 2px 8px; "
        f"border-radius: 12px; "
        f"font-size: 0.8em; "
        f"font-weight: 600;"
        f'">{icon} {label}</span>'
    )
    st.markdown(styled, unsafe_allow_html=True)
