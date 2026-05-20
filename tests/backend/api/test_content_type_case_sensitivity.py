"""Tests for case-insensitive content-type handling."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

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


@pytest_asyncio.fixture
async def mock_ollama():
    with patch("backend.core.models.ollama_client.ollama_client") as mock:
        mock.embed_texts = AsyncMock(return_value=[[0.1] * 768, [0.2] * 768])
        yield mock


@pytest.mark.asyncio
async def test_pdf_ingest_case_insensitive(client):
    """Test that PDF ingestion accepts case variations of application/pdf."""
    pdf_content = b"%PDF-1.4 fake pdf content " * 100

    with patch("backend.core.ingestion.pdf_ingestor.groundx_client") as mock_gx:
        mock_gx.upload_pdf = AsyncMock(return_value={"document_id": "doc-123"})

        # Test lowercase
        response = await client.post(
            "/api/ingest/pdf",
            files={"file": ("test.pdf", pdf_content, "application/pdf")},
        )
        assert response.status_code == 200

        # Test uppercase
        response = await client.post(
            "/api/ingest/pdf",
            files={"file": ("test.pdf", pdf_content, "APPLICATION/PDF")},
        )
        assert response.status_code == 200

        # Test mixed case
        response = await client.post(
            "/api/ingest/pdf",
            files={"file": ("test.pdf", pdf_content, "Application/Pdf")},
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_audio_ingest_case_insensitive(client, mock_ollama):
    """Test that audio ingestion accepts case variations of MIME types."""
    audio_content = b"fake audio content " * 100

    from unittest.mock import MagicMock

    # Mock Qdrant insertion
    mock_qdrant_upsert = AsyncMock()
    mock_qdrant_upsert.return_value = None

    # Patch the ollama_client import in audio_ingestor module
    with patch("backend.core.ingestion.audio_ingestor.ollama_client", new=mock_ollama):
        with patch("backend.core.ingestion.audio_ingestor.AudioIngestor._get_whisper_model") as mock_whisper:
            with patch("backend.core.ingestion.audio_ingestor.AudioIngestor._insert_chunks_to_qdrant", new=mock_qdrant_upsert):
                with patch("backend.core.ingestion.audio_ingestor.AudioIngestor._transcribe") as mock_transcribe:
                    # Setup transcribe mock - returns (text, duration, language)
                    mock_transcribe.return_value = ("Transcribed text", 10.0, "en")

                    # Test lowercase
                    response = await client.post(
                        "/api/ingest/audio",
                        files={"file": ("test.mp3", audio_content, "audio/mpeg")},
                    )
                    assert response.status_code == 200

                    # Test uppercase
                    response = await client.post(
                        "/api/ingest/audio",
                        files={"file": ("test.mp3", audio_content, "AUDIO/MPEG")},
                    )
                    assert response.status_code == 200

                    # Test mixed case
                    response = await client.post(
                        "/api/ingest/audio",
                        files={"file": ("test.mp3", audio_content, "Audio/Mpeg")},
                    )
                    assert response.status_code == 200


@pytest.mark.asyncio
async def test_image_ingest_case_insensitive(client, mock_ollama):
    """Test that image ingestion accepts case variations of MIME types."""
    image_content = b"fake image content " * 100

    # Patch ollama_client import in image_processor module
    with patch("backend.core.ingestion.image_processor.ollama_client", new=mock_ollama):
        with patch("backend.core.ingestion.image_processor.ImageProcessor._extract_text") as mock_ocr:
            mock_ocr.return_value = "Extracted text"

            # Test lowercase
            response = await client.post(
                "/api/ingest/image",
                files={"file": ("test.jpg", image_content, "image/jpeg")},
            )
            assert response.status_code == 200

            # Test uppercase
            response = await client.post(
                "/api/ingest/image",
                files={"file": ("test.jpg", image_content, "IMAGE/JPEG")},
            )
            assert response.status_code == 200

            # Test mixed case
            response = await client.post(
                "/api/ingest/image",
                files={"file": ("test.jpg", image_content, "Image/Jpeg")},
            )
            assert response.status_code == 200
