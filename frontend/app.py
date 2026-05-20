import streamlit as st

from frontend.state.session import init_session_state
from frontend.styles.load_css import load_css
from frontend.tabs.documents_tab import render_documents_tab
from frontend.utils.api_client import APIClient


def main() -> None:
    """Main entry point for the Streamlit frontend application."""
    st.set_page_config(
        page_title="Industrial AI Assistant",
        page_icon="🏭",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()
    load_css()

    api_client = APIClient()

    with st.sidebar:
        st.title("🏭 Industrial AI")
        st.markdown("---")

        st.subheader("Projects")
        st.info("No projects yet. Create one to get started.")

        st.markdown("---")

        st.subheader("Recent Chats")
        st.info("No chats yet. Start a new conversation!")

        st.markdown("---")

        health = api_client.health_check()
        if health.get("status") == "ok":
            st.success("Backend Connected")
        else:
            st.error("Backend Disconnected")

    tab_chat, tab_docs, tab_ocr, tab_analysis, tab_tools = st.tabs(
        ["💬 Chat", "📄 Documents", "🔍 OCR", "📊 Analysis", "⚙️ Tools"]
    )

    with tab_chat:
        st.header("Chat")
        st.info("Chat functionality will be available in a future phase.")

    with tab_docs:
        render_documents_tab(api_client)

    with tab_ocr:
        st.header("OCR")
        st.info("OCR functionality will be available in a future phase.")

    with tab_analysis:
        st.header("Analysis")
        st.info("Analysis tools will be available in a future phase.")

    with tab_tools:
        st.header("Tools")
        st.info("Additional tools will be available in a future phase.")


if __name__ == "__main__":
    main()
