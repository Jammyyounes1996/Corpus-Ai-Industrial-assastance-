import streamlit as st

from frontend.utils.api_client import APIClient
from frontend.utils.file_helpers import get_file_type, get_type_icon


UPLOAD_CONFIG = {
    "pdf": {
        "endpoint": "/api/ingest/pdf",
        "extensions": ["pdf"],
        "max_mb": 100,
        "label": "PDF Document",
    },
    "audio": {
        "endpoint": "/api/ingest/audio",
        "extensions": ["mp3", "wav", "m4a", "ogg"],
        "max_mb": 100,
        "label": "Audio File",
    },
    "image": {
        "endpoint": "/api/ingest/image",
        "extensions": ["jpg", "jpeg", "png", "webp"],
        "max_mb": 25,
        "label": "Image File",
    },
}


def render_file_uploader(api_client: APIClient) -> dict | None:
    """Render a multi-type file upload widget with progress feedback.

    Supports PDF, audio, and image uploads.

    Args:
        api_client: Backend API client instance.

    Returns:
        Ingestion result dict if upload succeeded, None otherwise.
    """
    st.subheader("Upload File")

    file_type = st.radio(
        "File type",
        options=["pdf", "audio", "image"],
        format_func=lambda x: f"{get_type_icon(x)} {UPLOAD_CONFIG[x]['label']}",
        horizontal=True,
        key="upload_type_selector",
    )

    config = UPLOAD_CONFIG[file_type]

    uploaded_file = st.file_uploader(
        f"Choose a {config['label']}",
        type=config["extensions"],
        help=f"Maximum file size: {config['max_mb']} MB",
        key=f"uploader_{file_type}",
    )

    if uploaded_file is not None:
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)

        col1, col2 = st.columns([3, 1])
        with col1:
            st.text(f"{uploaded_file.name} ({file_size_mb:.1f} MB)")
        with col2:
            st.metric("Size", f"{file_size_mb:.1f} MB")

        if st.button("Upload", key=f"upload_{file_type}_btn", type="primary"):
            if file_size_mb > config["max_mb"]:
                st.error(
                    f"File too large: {file_size_mb:.1f} MB "
                    f"exceeds the {config['max_mb']} MB limit."
                )
                return None

            spinner_msg = {
                "pdf": "Uploading and processing PDF...",
                "audio": "Transcribing audio (this may take a while)...",
                "image": "Processing image OCR...",
            }

            with st.spinner(spinner_msg.get(file_type, "Uploading...")):
                try:
                    result = api_client.upload_file(
                        config["endpoint"],
                        file_data=uploaded_file.getvalue(),
                        filename=uploaded_file.name,
                    )
                    st.success(f"File '{uploaded_file.name}' uploaded successfully!")
                    st.json(result)
                    return result

                except Exception as exc:
                    error_detail = ""
                    if hasattr(exc, "response") and exc.response is not None:
                        try:
                            body = exc.response.json()
                            error_detail = body.get("detail", {}).get("message", str(exc))
                        except Exception:
                            error_detail = str(exc)
                    else:
                        error_detail = str(exc)

                    st.error(f"Upload failed: {error_detail}")
                    return None

    return None
