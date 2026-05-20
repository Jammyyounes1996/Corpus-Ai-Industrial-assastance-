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


@pytest.mark.asyncio
async def test_ingest_pdf_valid(client):
    pdf_content = b"%PDF-1.4 fake pdf content " * 100
    files = {"file": ("test.pdf", pdf_content, "application/pdf")}

    with patch("backend.core.ingestion.pdf_ingestor.groundx_client") as mock_gx:
        mock_gx.upload_pdf = AsyncMock(return_value={"document_id": "doc-123"})

        response = await client.post("/api/ingest/pdf", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.pdf"
    assert data["status"] == "processing"
    assert data["size_bytes"] == len(pdf_content)
    assert "file_id" in data


@pytest.mark.asyncio
async def test_ingest_pdf_invalid_type(client):
    files = {"file": ("test.jpg", b"fake image", "image/jpeg")}
    response = await client.post("/api/ingest/pdf", files=files)

    assert response.status_code == 415
    data = response.json()
    assert "UnsupportedMediaType" in data["detail"]["error"]


@pytest.mark.asyncio
async def test_ingest_pdf_oversized(client):
    with patch("backend.api.routes.ingest.pdf_ingestor") as mock_ingestor:
        mock_ingestor.ingest_pdf = AsyncMock(
            side_effect=ValueError("File size (101.0 MB) exceeds maximum (100 MB) for PDF files")
        )
        small_content = b"%PDF fake"
        files = {"file": ("big.pdf", small_content, "application/pdf")}
        response = await client.post("/api/ingest/pdf", files=files)

    assert response.status_code == 413
    data = response.json()
    assert "exceeds" in data["detail"]["message"]
