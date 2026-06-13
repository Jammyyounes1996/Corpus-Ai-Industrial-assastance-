import pytest
import pytest_asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

from backend.main import app
from backend.database.database import get_session
from backend.database import crud


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _create_pdf_file(db_session, disk_path: str = "/fake/test.pdf"):
    return await crud.create_file(
        db_session,
        original_name="test.pdf",
        file_type="pdf",
        disk_path=disk_path,
        size_bytes=1024,
    )


async def _create_image_file(db_session):
    return await crud.create_file(
        db_session,
        original_name="test.jpg",
        file_type="image",
        disk_path="/fake/test.jpg",
        size_bytes=512,
    )


@pytest.mark.asyncio
async def test_extract_pdf_ocr_success(client, db_session):
    db_file = await _create_pdf_file(db_session)

    with patch("backend.core.ingestion.pdf_ocr_processor.PdfOcrProcessor._render_pages") as mock_render, \
         patch("backend.core.ingestion.pdf_ocr_processor.PdfOcrProcessor._ocr_page") as mock_ocr, \
         patch("backend.core.ingestion.pdf_ocr_processor.Path") as mock_path_cls:
        mock_path_cls.return_value.exists.return_value = True
        mock_render.return_value = [b"fake_png_bytes_page1", b"fake_png_bytes_page2"]
        mock_ocr.side_effect = ["Text from page 1", "Text from page 2"]

        response = await client.post(f"/api/ocr/{db_file.id}/extract")

    assert response.status_code == 200
    data = response.json()
    assert data["file_id"] == db_file.id
    assert data["pages_processed"] == 2
    assert data["cached"] is False
    assert "PAGE 1" in data["extracted_text"]
    assert "Text from page 1" in data["extracted_text"]


@pytest.mark.asyncio
async def test_extract_pdf_ocr_cached(client, db_session):
    db_file = await _create_pdf_file(db_session)

    from backend.database.models import OCRResult
    ocr = OCRResult(
        file_id=db_file.id,
        extracted_text="--- PAGE 1 ---\nCached text",
        model_used="gemma4:12b",
    )
    db_session.add(ocr)
    await db_session.flush()

    with patch("backend.core.ingestion.pdf_ocr_processor.PdfOcrProcessor._render_pages") as mock_render:
        response = await client.post(f"/api/ocr/{db_file.id}/extract")
        mock_render.assert_not_called()

    assert response.status_code == 200
    data = response.json()
    assert data["cached"] is True
    assert "Cached text" in data["extracted_text"]


@pytest.mark.asyncio
async def test_extract_pdf_ocr_file_not_found(client, db_session):
    response = await client.post("/api/ocr/nonexistent-id/extract")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_extract_pdf_ocr_wrong_file_type(client, db_session):
    db_file = await _create_image_file(db_session)
    response = await client.post(f"/api/ocr/{db_file.id}/extract")
    assert response.status_code == 400
    assert "InvalidFileType" in response.json()["detail"]["error"]


@pytest.mark.asyncio
async def test_extract_pdf_ocr_missing_disk_file(client, db_session):
    db_file = await _create_pdf_file(db_session, disk_path="/nonexistent/path.pdf")

    with patch("backend.core.ingestion.pdf_ocr_processor.PdfOcrProcessor._render_pages") as mock_render:
        mock_render.side_effect = FileNotFoundError("PDF not found: /nonexistent/path.pdf")
        response = await client.post(f"/api/ocr/{db_file.id}/extract")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_pdf_ocr_max_pages_respected(db_session):
    from backend.core.ingestion.pdf_ocr_processor import PdfOcrProcessor

    processor = PdfOcrProcessor()

    mock_doc = MagicMock()
    mock_doc.__len__ = MagicMock(return_value=30)
    mock_doc.__getitem__ = MagicMock()

    mock_page = MagicMock()
    mock_pix = MagicMock()
    mock_pix.width = 100
    mock_pix.height = 100
    mock_pix.samples = b"\x00" * (100 * 100 * 3)
    mock_page.get_pixmap.return_value = mock_pix
    mock_doc.__getitem__ = lambda self, idx: mock_page

    with patch("fitz.open", return_value=mock_doc), \
         patch("backend.core.ingestion.pdf_ocr_processor.Path") as mock_path_cls, \
         patch.object(processor, "_ocr_page", new_callable=AsyncMock, return_value="text"):
        mock_path_cls.return_value.exists.return_value = True
        result = await processor.extract_text(
            db_session,
            file_id="test-id",
            pdf_path="/fake/test.pdf",
        )

    assert result["pages_processed"] == 20


@pytest.mark.asyncio
async def test_render_pages_no_access_after_close(db_session):
    from backend.core.ingestion.pdf_ocr_processor import PdfOcrProcessor

    processor = PdfOcrProcessor()

    closed_flag = {"closed": False}

    class StrictDoc:
        def __init__(self):
            self._pages = 2

        def __len__(self):
            if closed_flag["closed"]:
                raise RuntimeError("document closed")
            return self._pages

        def __getitem__(self, idx):
            if closed_flag["closed"]:
                raise RuntimeError("document closed")
            mock_page = MagicMock()
            mock_pix = MagicMock()
            mock_pix.width = 10
            mock_pix.height = 10
            mock_pix.samples = b"\x00" * 300
            mock_page.get_pixmap.return_value = mock_pix
            return mock_page

        def close(self):
            closed_flag["closed"] = True

    with patch("fitz.open", return_value=StrictDoc()), \
         patch("backend.core.ingestion.pdf_ocr_processor.Path") as mock_path_cls, \
         patch.object(processor, "_ocr_page", new_callable=AsyncMock, return_value="page text"):
        mock_path_cls.return_value.exists.return_value = True
        result = await processor.extract_text(
            db_session,
            file_id="test-doc-closed",
            pdf_path="/fake/closed_test.pdf",
        )

    assert result["pages_processed"] == 2
    assert result["file_id"] == "test-doc-closed"
    assert "page text" in result["extracted_text"]


@pytest.mark.asyncio
async def test_render_pages_converts_to_bytes_before_close():
    from backend.core.ingestion.pdf_ocr_processor import PdfOcrProcessor

    processor = PdfOcrProcessor()

    closed_flag = {"closed": False}
    pixmap_refs = []

    class TrackingDoc:
        def __init__(self):
            pass

        def __len__(self):
            if closed_flag["closed"]:
                raise RuntimeError("document closed")
            return 1

        def __getitem__(self, idx):
            if closed_flag["closed"]:
                raise RuntimeError("document closed")
            mock_page = MagicMock()
            mock_pix = MagicMock()
            mock_pix.width = 8
            mock_pix.height = 8
            mock_pix.samples = b"\x00" * (8 * 8 * 3)
            mock_page.get_pixmap.return_value = mock_pix
            pixmap_refs.append(mock_pix)
            return mock_page

        def close(self):
            closed_flag["closed"] = True

    with patch("fitz.open", return_value=TrackingDoc()), \
         patch("backend.core.ingestion.pdf_ocr_processor.Path") as mock_path_cls:
        mock_path_cls.return_value.exists.return_value = True
        pages = processor._render_pages("/fake/bytes_test.pdf")

    assert len(pages) == 1
    assert isinstance(pages[0], bytes)
    assert len(pages[0]) > 0


@pytest.mark.asyncio
async def test_extract_endpoint_no_document_closed_error(client, db_session):
    db_file = await _create_pdf_file(db_session)

    with patch("backend.core.ingestion.pdf_ocr_processor.PdfOcrProcessor._render_pages") as mock_render, \
         patch("backend.core.ingestion.pdf_ocr_processor.PdfOcrProcessor._ocr_page") as mock_ocr, \
         patch("backend.core.ingestion.pdf_ocr_processor.Path") as mock_path_cls:
        mock_path_cls.return_value.exists.return_value = True
        mock_render.return_value = [b"page1_bytes"]
        mock_ocr.return_value = "Extracted OCR text"

        response = await client.post(f"/api/ocr/{db_file.id}/extract")

    assert response.status_code == 200
    data = response.json()
    assert "document closed" not in data.get("extracted_text", "")
    assert "Extracted OCR text" in data["extracted_text"]


@pytest.mark.asyncio
async def test_extract_returns_clean_500_on_internal_error(client, db_session):
    db_file = await _create_pdf_file(db_session)

    with patch("backend.core.ingestion.pdf_ocr_processor.PdfOcrProcessor._render_pages") as mock_render, \
         patch("backend.core.ingestion.pdf_ocr_processor.Path") as mock_path_cls:
        mock_path_cls.return_value.exists.return_value = True
        mock_render.side_effect = RuntimeError("document closed")

        response = await client.post(f"/api/ocr/{db_file.id}/extract")

    assert response.status_code == 500
    data = response.json()
    assert data["detail"]["error"] == "OCRError"
    assert data["detail"]["message"] == "PDF OCR extraction failed while rendering pages."
    assert "document closed" not in data["detail"]["message"]
