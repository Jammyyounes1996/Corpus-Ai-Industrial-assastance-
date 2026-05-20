from datetime import datetime

import streamlit as st

from frontend.components.status_badge import render_status_badge
from frontend.utils.file_helpers import format_size, get_type_icon


def _format_date(dt_str: str) -> str:
    """Format ISO datetime string to readable format."""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return dt_str


def render_file_card(file_data: dict) -> None:
    """Render a file display card with metadata and status badge.

    Args:
        file_data: Dict with keys: id, original_name, file_type, size_bytes,
                   indexing_status, error_message, created_at,
                   transcript_summary (optional), ocr_summary (optional).
    """
    file_type = file_data.get("file_type", "unknown")
    status = file_data.get("indexing_status", "pending")

    with st.container():
        col_icon, col_info, col_status = st.columns([1, 6, 2])

        with col_icon:
            st.markdown(
                f"<div style='font-size: 2em; text-align: center;'>"
                f"{get_type_icon(file_type)}</div>",
                unsafe_allow_html=True,
            )

        with col_info:
            st.markdown(f"**{file_data.get('original_name', 'Unknown')}**")
            size_str = format_size(file_data.get("size_bytes", 0))
            date_str = _format_date(file_data.get("created_at", ""))
            st.caption(f"{file_type.upper()} · {size_str} · {date_str}")

            transcript = file_data.get("transcript_summary")
            if transcript:
                dur = transcript.get("duration_seconds", 0)
                lang = transcript.get("language", "unknown")
                st.caption(f"Duration: {dur:.1f}s · Language: {lang}")

            ocr = file_data.get("ocr_summary")
            if ocr:
                preview = ocr.get("text_preview", "")
                if preview:
                    st.caption(f"OCR: {preview[:80]}{'...' if len(preview) > 80 else ''}")

            error = file_data.get("error_message")
            if error and status == "failed":
                st.error(f"Error: {error}")

        with col_status:
            render_status_badge(status)

        st.markdown("---")
