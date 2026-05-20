import streamlit as st

from frontend.components.delete_confirmation import render_delete_confirmation
from frontend.components.file_card import render_file_card
from frontend.components.file_uploader import render_file_uploader
from frontend.utils.api_client import APIClient
from frontend.utils.file_helpers import get_type_icon


def render_documents_tab(api_client: APIClient) -> None:
    """Render the Documents tab with upload widget, filtering, sorting, and file grid.

    Args:
        api_client: Backend API client instance.
    """
    st.header("Document Management")

    col_upload, col_list = st.columns([1, 2])

    with col_upload:
        render_file_uploader(api_client)

    with col_list:
        filter_col, sort_col = st.columns(2)

        with filter_col:
            type_filter = st.selectbox(
                "Filter by type",
                options=["all", "pdf", "audio", "image"],
                format_func=lambda x: f"{get_type_icon(x) if x != 'all' else '📂'} {x.title()}",
                key="doc_type_filter",
            )

        with sort_col:
            sort_option = st.selectbox(
                "Sort by",
                options=["date_desc", "date_asc", "name"],
                format_func=lambda x: {
                    "date_desc": "Newest First",
                    "date_asc": "Oldest First",
                    "name": "Name (A-Z)",
                }[x],
                key="doc_sort",
            )

        st.markdown("---")

        try:
            params = {"sort": sort_option, "limit": 100}
            if type_filter != "all":
                params["type"] = type_filter

            files = api_client.get("/api/files", params=params)

            file_list = files.get("files", [])
            if not file_list:
                st.info("No documents found. Upload a file to get started!")
            else:
                st.caption(f"Showing {len(file_list)} file(s)")
                for file_data in file_list:
                    file_id = file_data.get("id", "")
                    file_name = file_data.get("original_name", "Unknown")

                    render_file_card(file_data)

                    delete_key = f"del_btn_{file_id}"
                    if st.button("Delete", key=delete_key):
                        st.session_state[f"pending_delete_{file_id}"] = True
                        st.rerun()

                    if st.session_state.get(f"pending_delete_{file_id}"):
                        if render_delete_confirmation(file_name, file_id):
                            try:
                                api_client.delete(f"/api/files/{file_id}")
                                st.success(f"File '{file_name}' deleted.")
                                st.session_state.pop(f"pending_delete_{file_id}", None)
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Delete failed: {exc}")
                                st.session_state.pop(f"pending_delete_{file_id}", None)
                        else:
                            if st.button("Dismiss", key=f"dismiss_{file_id}"):
                                st.session_state.pop(f"pending_delete_{file_id}", None)
                                st.rerun()

        except Exception as exc:
            st.warning(f"Could not load documents: {exc}")
            st.info("Make sure the backend is running.")
