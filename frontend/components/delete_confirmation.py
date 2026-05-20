import streamlit as st


def render_delete_confirmation(file_name: str, file_id: str) -> bool:
    """Render a delete confirmation dialog.

    Args:
        file_name: Display name of the file.
        file_id: Unique file identifier.

    Returns:
        True if user confirmed deletion, False otherwise.
    """
    st.warning(f"Are you sure you want to delete **{file_name}**?")
    st.caption("This will remove the file from disk, database, and search index. This cannot be undone.")

    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        confirmed = st.button(
            "Delete",
            key=f"confirm_delete_{file_id}",
            type="primary",
        )
    with col_cancel:
        cancelled = st.button(
            "Cancel",
            key=f"cancel_delete_{file_id}",
        )

    if cancelled:
        return False
    return confirmed
