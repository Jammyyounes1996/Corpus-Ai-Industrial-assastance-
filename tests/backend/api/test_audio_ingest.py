import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

from backend.main import app
from backend.database.database import get_session


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ingest_audio_valid(client):
    audio_content = b"fake mp3 audio data " * 500
    files = {"file": ("test.mp3", audio_content, "audio/mpeg")}

    with patch("backend.core.ingestion.audio_ingestor.AudioIngestor._get_whisper_model") as mock_whisper, \
         patch("backend.core.ingestion.audio_ingestor.ollama_client") as mock_ollama, \
         patch("qdrant_client.QdrantClient") as mock_qdrant_cls:

        fake_model = MagicMock()
        fake_segment = MagicMock()
        fake_segment.text = "Hello world this is a test."
        fake_info = MagicMock()
        fake_info.language = "en"
        fake_info.duration = 10.5
        fake_model.transcribe.return_value = ([fake_segment], fake_info)
        mock_whisper.return_value = fake_model

        mock_ollama.embed_texts = AsyncMock(return_value=[[0.1] * 768])

        mock_qdrant = MagicMock()
        mock_qdrant_cls.return_value = mock_qdrant

        response = await client.post("/api/ingest/audio", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.mp3"
    assert data["status"] == "indexed"
    assert data["size_bytes"] == len(audio_content)
    assert "duration_seconds" in data
    assert "language" in data


@pytest.mark.asyncio
async def test_ingest_audio_invalid_type(client):
    files = {"file": ("test.mp4", b"fake video", "video/mp4")}
    response = await client.post("/api/ingest/audio", files=files)

    assert response.status_code == 415
    data = response.json()
    assert "UnsupportedMediaType" in data["detail"]["error"]


@pytest.mark.asyncio
async def test_ingest_audio_oversized(client):
    big_content = b"x" * (101 * 1024 * 1024)
    files = {"file": ("big.mp3", big_content, "audio/mpeg")}
    response = await client.post("/api/ingest/audio", files=files)

    assert response.status_code == 413
    data = response.json()
    assert "PayloadTooLarge" in data["detail"]["error"]
