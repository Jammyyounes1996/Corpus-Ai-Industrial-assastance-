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
async def test_ingest_image_valid(client):
    image_content = b"\xff\xd8\xff\xe0 fake jpeg data " * 100
    files = {"file": ("test.jpg", image_content, "image/jpeg")}

    with patch("backend.core.ingestion.image_processor.ImageProcessor._extract_text") as mock_ocr:
        mock_ocr.return_value = "Extracted text from industrial document"
        response = await client.post("/api/ingest/image", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.jpg"
    assert data["status"] == "indexed"
    assert data["size_bytes"] == len(image_content)


@pytest.mark.asyncio
async def test_ingest_image_invalid_type(client):
    files = {"file": ("test.pdf", b"fake pdf", "application/pdf")}
    response = await client.post("/api/ingest/image", files=files)

    assert response.status_code == 415
    data = response.json()
    assert "UnsupportedMediaType" in data["detail"]["error"]


@pytest.mark.asyncio
async def test_ingest_image_oversized(client):
    big_content = b"x" * (26 * 1024 * 1024)
    files = {"file": ("big.jpg", big_content, "image/jpeg")}
    response = await client.post("/api/ingest/image", files=files)

    assert response.status_code == 413
    data = response.json()
    assert "PayloadTooLarge" in data["detail"]["error"]
