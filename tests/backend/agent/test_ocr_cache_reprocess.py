from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.agent.nodes.ocr import (
    _is_bad_ocr,
    _normalize_ocr_text,
    NO_READABLE_TEXT_MESSAGE,
    ocr_node,
)
from backend.database import crud

_OLD_MODEL = "joe-speedboat/Gemma-4-Uncensored-HauhauCS-Aggressive:e4b"
_NEW_MODEL = "gemma4:12b"


class TestIsBadOcrAutoRepetition:
    def test_auto_repeated_returns_true(self):
        assert _is_bad_ocr("Auto Auto Auto Auto Auto Auto Auto") is True

    def test_auto_repeated_many_times(self):
        text = " ".join(["Auto"] * 50)
        assert _is_bad_ocr(text) is True


class TestIsBadOcrModelStaleness:
    def test_stale_model_bad_even_with_valid_text(self):
        text = "Safety valve PSV-101 set at 200 psig. Last inspected 2024-01-15."
        assert _is_bad_ocr(text) is False
        assert _is_bad_ocr(text, expected_model=_NEW_MODEL, cached_model=_OLD_MODEL) is True

    def test_current_model_passes(self):
        text = "Safety valve PSV-101 set at 200 psig. Last inspected 2024-01-15."
        assert _is_bad_ocr(text, expected_model=_NEW_MODEL, cached_model=_NEW_MODEL) is False


@pytest.mark.asyncio
async def test_bad_cached_ocr_with_stale_model_triggers_reprocess(db_session, tmp_path):
    image_path = tmp_path / "panel.png"
    image_path.write_bytes(b"fake png bytes 1234567890")

    image_file = await crud.create_file(
        db_session,
        original_name="panel.png",
        file_type="image",
        disk_path=str(image_path),
        size_bytes=20,
    )
    await crud.create_ocr_result(
        db_session,
        file_id=image_file.id,
        extracted_text="Safety valve PSV-101 set at 200 psig. Last inspected 2024-01-15.",
        model_used=_OLD_MODEL,
    )

    good_text = "Pressure gauge reading 4.5 bar on compressor unit CP-101 nominal"
    with patch(
        "backend.agent.nodes.ocr.image_processor._extract_text",
        new=AsyncMock(return_value=good_text),
    ):
        mock_settings = MagicMock()
        mock_settings.OCR_MODEL_NAME = _NEW_MODEL
        with patch("backend.agent.nodes.ocr.image_processor._settings", mock_settings):
            result = await ocr_node(
                {"query": "extract text", "answer_mode": "general", "attached_files": [image_file.id]},
                db_session,
            )

    assert result["ocr_called"] is True
    assert result["ocr_results"][0]["content"] == good_text

    updated = await crud.get_ocr_result_by_file_id(db_session, image_file.id)
    assert updated.extracted_text == good_text
    assert updated.model_used == _NEW_MODEL


@pytest.mark.asyncio
async def test_11png_meta_commentary_cached_triggers_reprocess(db_session, tmp_path):
    image_path = tmp_path / "11.png"
    image_path.write_bytes(b"fake 11 png bytes")

    image_file = await crud.create_file(
        db_session,
        original_name="11.png",
        file_type="image",
        disk_path=str(image_path),
        size_bytes=20,
    )
    await crud.create_ocr_result(
        db_session,
        file_id=image_file.id,
        extracted_text="[\n:\n] \n(The text is mostly composed of single characters or very short words/symbols)",
        model_used=_OLD_MODEL,
    )

    good_text = "Temperature sensor TI-201 reading 45.3 degrees Celsius nominal operation"
    with patch(
        "backend.agent.nodes.ocr.image_processor._extract_text",
        new=AsyncMock(return_value=good_text),
    ):
        mock_settings = MagicMock()
        mock_settings.OCR_MODEL_NAME = _NEW_MODEL
        with patch("backend.agent.nodes.ocr.image_processor._settings", mock_settings):
            result = await ocr_node(
                {"query": "extract text", "answer_mode": "general", "attached_files": [image_file.id]},
                db_session,
            )

    assert result["ocr_called"] is True
    assert result["ocr_results"][0]["content"] == good_text

    updated = await crud.get_ocr_result_by_file_id(db_session, image_file.id)
    assert updated.model_used == _NEW_MODEL


@pytest.mark.asyncio
async def test_stale_model_reprocess_still_bad_returns_fallback(db_session, tmp_path):
    image_path = tmp_path / "gauge.jpg"
    image_path.write_bytes(b"fake jpg bytes")

    image_file = await crud.create_file(
        db_session,
        original_name="gauge.jpg",
        file_type="image",
        disk_path=str(image_path),
        size_bytes=14,
    )
    await crud.create_ocr_result(
        db_session,
        file_id=image_file.id,
        extracted_text="Auto Auto Auto Auto Auto Auto Auto",
        model_used=_OLD_MODEL,
    )

    with patch(
        "backend.agent.nodes.ocr.image_processor._extract_text",
        new=AsyncMock(return_value="Auto Auto Auto Auto Auto"),
    ):
        mock_settings = MagicMock()
        mock_settings.OCR_MODEL_NAME = _NEW_MODEL
        with patch("backend.agent.nodes.ocr.image_processor._settings", mock_settings):
            result = await ocr_node(
                {"query": "extract text", "answer_mode": "general", "attached_files": [image_file.id]},
                db_session,
            )

    assert result["ocr_called"] is True
    assert result["ocr_results"][0]["content"] == NO_READABLE_TEXT_MESSAGE


@pytest.mark.asyncio
async def test_valid_cache_with_current_model_not_reprocessed(db_session):
    image_file = await crud.create_file(
        db_session,
        original_name="good_label.png",
        file_type="image",
        disk_path="data/uploads/good_label.png",
        size_bytes=10,
    )
    good_text = "Pressure gauge reading 4.5 bar on compressor unit CP-101 nominal"
    await crud.create_ocr_result(
        db_session,
        file_id=image_file.id,
        extracted_text=good_text,
        model_used=_NEW_MODEL,
    )

    with patch("backend.agent.nodes.ocr.image_processor._extract_text", new_callable=AsyncMock) as mock_extract:
        mock_settings = MagicMock()
        mock_settings.OCR_MODEL_NAME = _NEW_MODEL
        with patch("backend.agent.nodes.ocr.image_processor._settings", mock_settings):
            result = await ocr_node(
                {"query": "extract text", "answer_mode": "general", "attached_files": [image_file.id]},
                db_session,
            )

    assert result["ocr_called"] is True
    assert result["ocr_results"][0]["content"] == good_text
    mock_extract.assert_not_called()


@pytest.mark.asyncio
async def test_1png_prompt_echo_cached_triggers_reprocess(db_session, tmp_path):
    image_path = tmp_path / "1.png"
    image_path.write_bytes(b"fake 1 png bytes")

    image_file = await crud.create_file(
        db_session,
        original_name="1.png",
        file_type="image",
        disk_path=str(image_path),
        size_bytes=20,
    )
    await crud.create_ocr_result(
        db_session,
        file_id=image_file.id,
        extracted_text="[:]\nExtract all text from this image.\n[:]\n[:]\n[:]\n[:]",
        model_used=_OLD_MODEL,
    )

    good_text = "Flow meter FM-301 shows 250 GPM throughput on main pipeline segment"
    with patch(
        "backend.agent.nodes.ocr.image_processor._extract_text",
        new=AsyncMock(return_value=good_text),
    ):
        mock_settings = MagicMock()
        mock_settings.OCR_MODEL_NAME = _NEW_MODEL
        with patch("backend.agent.nodes.ocr.image_processor._settings", mock_settings):
            result = await ocr_node(
                {"query": "extract text", "answer_mode": "general", "attached_files": [image_file.id]},
                db_session,
            )

    assert result["ocr_called"] is True
    assert result["ocr_results"][0]["content"] == good_text

    updated = await crud.get_ocr_result_by_file_id(db_session, image_file.id)
    assert updated.model_used == _NEW_MODEL


@pytest.mark.asyncio
async def test_no_attached_files_returns_empty(db_session):
    state = {"query": "hello", "answer_mode": "general", "attached_files": []}
    result = await ocr_node(state, db_session)
    assert result["ocr_called"] is False
    assert result["ocr_results"] == []
