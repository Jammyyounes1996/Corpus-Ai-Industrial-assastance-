import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, ASGITransport

from backend.main import app
from backend.database import crud
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
        mock_gx.upload_pdf = AsyncMock(return_value={
            "status": "queued",
            "process_id": "proc-123",
            "document_id": "doc-123",
            "bucket_id": "28306",
        })

        response = await client.post("/api/ingest/pdf", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.pdf"
    assert data["status"] == "queued"
    assert data["indexing_status"] == "queued"
    assert data["size"] == len(pdf_content)
    assert data["groundx_process_id"] == "proc-123"
    assert data["groundx_bucket_id"] == "28306"
    assert "file_id" in data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("groundx_status", "expected_status", "ready", "error_message"),
    [
        ({"status": "processing", "process_id": "proc-1", "bucket_id": "28306", "document_id": None}, "processing", False, None),
        ({"status": "indexed", "process_id": "proc-1", "bucket_id": "28306", "document_id": "doc-1"}, "indexed", True, None),
        ({"status": "failed", "process_id": "proc-1", "bucket_id": "28306", "document_id": None, "error_message": "boom"}, "failed", False, "boom"),
    ],
)
async def test_get_pdf_status_refreshes_groundx_state(
    client,
    db_session,
    groundx_status,
    expected_status,
    ready,
    error_message,
):
    db_file = await crud.create_file(
        db_session,
        original_name="status.pdf",
        file_type="pdf",
        disk_path="data/uploads/status.pdf",
        size_bytes=42,
        groundx_process_id="proc-1",
        groundx_bucket_id="28306",
    )
    await crud.update_file_indexing_status(
        db_session,
        db_file.id,
        status="processing",
        groundx_process_id="proc-1",
        groundx_bucket_id="28306",
        status_message="Processing in GroundX",
    )
    await db_session.commit()

    with patch("backend.core.ingestion.pdf_ingestor.groundx_client") as mock_gx:
        mock_gx.get_processing_status = AsyncMock(return_value=groundx_status)
        response = await client.get(f"/api/files/{db_file.id}/status")

    assert response.status_code == 200
    data = response.json()
    assert data["file_id"] == db_file.id
    assert data["groundx_process_id"] == "proc-1"
    assert data["groundx_bucket_id"] == "28306"
    assert data["indexing_status"] == expected_status
    assert data["ready_for_groundx_retrieval"] is ready
    assert data["error_message"] == error_message


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
