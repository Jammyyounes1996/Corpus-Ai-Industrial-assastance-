from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All configuration is managed through environment variables.
    A .env file in the project root is automatically loaded.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "Industrial AI Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8001

    FRONTEND_URL: str = "http://localhost:8501"

    DATABASE_URL: str = "sqlite+aiosqlite:///./industrial_ai.db"

    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "industrial_assistant"
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANKER_TOP_K: int = 8
    RERANKER_ENABLED: bool = True

    GROUNDX_API_KEY: str = ""
    GROUNDX_BUCKET_ID: int = 0

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "joe-speedboat/Gemma-4-Uncensored-HauhauCS-Aggressive:e4b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text:latest"

    WHISPER_DEVICE: str = "auto"
    WHISPER_COMPUTE_TYPE: str = "auto"
    WHISPER_MODEL: str = "base"

    MAX_PDF_SIZE_MB: int = 100
    MAX_AUDIO_SIZE_MB: int = 100
    MAX_IMAGE_SIZE_MB: int = 25

    SECRET_KEY: str = "REPLACE_WITH_GENERATED_FERNET_KEY"

    DEFAULT_MODEL_PROVIDER: str = "ollama"
    DEFAULT_MODEL_NAME: str = "joe-speedboat/Gemma-4-Uncensored-HauhauCS-Aggressive:e4b"
    MAX_MESSAGE_LENGTH: int = 10000
    MAX_ATTACHED_FILES: int = 10
    MAX_THINKING_STEPS_DISPLAY: int = 3
    CONVERSATION_SUMMARY_LIMIT: int = 50
    DEFAULT_THEME: str = "light"

    LOG_LEVEL: str = "INFO"

    @property
    def max_pdf_size_bytes(self) -> int:
        return self.MAX_PDF_SIZE_MB * 1024 * 1024

    @property
    def max_audio_size_bytes(self) -> int:
        return self.MAX_AUDIO_SIZE_MB * 1024 * 1024

    @property
    def max_image_size_bytes(self) -> int:
        return self.MAX_IMAGE_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
