from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.database.database import Base


SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,
    future=True,
)

TestingAsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestingAsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_groundx():
    with patch("backend.core.retrieval.groundx_client.groundx_client") as mock:
        mock.upload_pdf = AsyncMock(return_value={"document_id": "test-doc-123"})
        mock.poll_indexing_status = AsyncMock(
            return_value={"status": "complete", "error_message": None}
        )
        yield mock


@pytest.fixture
def mock_ollama_embed():
    with patch("backend.core.models.ollama_client.ollama_client") as mock:
        mock.embed_text = AsyncMock(return_value=[0.1] * 768)
        mock.embed_texts = AsyncMock(return_value=[[0.1] * 768, [0.2] * 768])
        mock.generate = AsyncMock(return_value="Extracted text from image")
        yield mock


@pytest.fixture
def mock_whisper():
    with patch("backend.core.ingestion.audio_ingestor.AudioIngestor._get_whisper_model") as mock:
        fake_model = MagicMock()
        fake_segment = MagicMock()
        fake_segment.text = "Hello world this is a test."
        fake_info = MagicMock()
        fake_info.language = "en"
        fake_info.duration = 10.5
        fake_model.transcribe.return_value = ([fake_segment], fake_info)
        mock.return_value = fake_model
        yield mock


@pytest.fixture
def mock_qdrant():
    with patch("qdrant_client.QdrantClient") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.upsert = MagicMock()
        yield mock_client
