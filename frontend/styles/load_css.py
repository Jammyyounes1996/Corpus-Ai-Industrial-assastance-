import streamlit as st


def load_css(file_path: str = "frontend/styles/main.css") -> None:
    """Load and inject a CSS file into the Streamlit app.

    Args:
        file_path: Path to the CSS file relative to the project root.
    """
    try:
        with open(file_path) as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"CSS file not found: {file_path}")
