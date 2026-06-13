from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.agent.graph import _retrieval_route
from backend.agent.nodes.qdrant import qdrant_retrieve_node
from backend.agent.nodes.groundx import groundx_retrieve_node
from backend.agent.nodes.ocr import ocr_node
from backend.agent.nodes.router import router_node
from backend.database import crud


# ── Qdrant tests ──


@pytest.mark.asyncio
async def test_qdrant_skipped_in_general_mode():
    state = {"query": "test", "answer_mode": "general"}
    result = await qdrant_retrieve_node(state)
    assert result["qdrant_called"] is False
    assert result["qdrant_results"] == []


@pytest.mark.asyncio
async def test_qdrant_skipped_in_groundx_mode():
    state = {"query": "test", "answer_mode": "groundx"}
    result = await qdrant_retrieve_node(state)
    assert result["qdrant_called"] is False
    assert result["qdrant_results"] == []


@pytest.mark.asyncio
async def test_qdrant_runs_in_audio_mode_with_audio_filter():
    mock_retriever = MagicMock(
        hybrid_query=AsyncMock(return_value=[])
    )
    with patch("backend.agent.nodes.qdrant.qdrant_retriever", mock_retriever):
        state = {"query": "find audio recordings", "answer_mode": "audio"}
        result = await qdrant_retrieve_node(state)

    assert result["qdrant_called"] is True
    assert result["qdrant_global_audio_search_allowed"] is True
    mock_retriever.hybrid_query.assert_called_once_with(
        query_text="find audio recordings",
        limit=15,
        file_id_filter=None,
    )


@pytest.mark.asyncio
async def test_qdrant_audio_results_only_file_type_audio():
    chunks = [
        {
            "id": "chunk-a1",
            "score": 0.85,
            "payload": {
                "chunk_text": "audio transcript content",
                "file_id": "audio-001",
                "file_type": "audio",
                "chunk_index": 0,
                "original_name": "meeting_recording.mp3",
            },
        },
        {
            "id": "chunk-p1",
            "score": 0.90,
            "payload": {
                "chunk_text": "pdf document content",
                "file_id": "pdf-001",
                "file_type": "pdf",
                "chunk_index": 0,
                "original_name": "report.pdf",
            },
        },
        {
            "id": "chunk-a2",
            "score": 0.75,
            "payload": {
                "chunk_text": "another audio segment",
                "file_id": "audio-002",
                "file_type": "audio",
                "chunk_index": 1,
                "original_name": "",
            },
        },
    ]
    mock_retriever = MagicMock(hybrid_query=AsyncMock(return_value=chunks))
    with patch("backend.agent.nodes.qdrant.qdrant_retriever", mock_retriever):
        state = {"query": "audio query", "answer_mode": "audio"}
        result = await qdrant_retrieve_node(state)

    assert result["qdrant_called"] is True
    assert len(result["qdrant_results"]) == 2
    assert all(r["file_type"] == "audio" for r in result["qdrant_results"])
    names = [r["file_name"] for r in result["qdrant_results"]]
    assert "meeting_recording.mp3" in names
    assert any(n.startswith("Audio file") for n in names)


# ── GroundX tests ──


@pytest.mark.asyncio
async def test_groundx_skipped_in_general_mode():
    state = {"query": "test", "answer_mode": "general"}
    result = await groundx_retrieve_node(state)
    assert result["groundx_called"] is False
    assert result["groundx_results"] == []


@pytest.mark.asyncio
async def test_groundx_skipped_in_audio_mode():
    state = {"query": "test", "answer_mode": "audio"}
    result = await groundx_retrieve_node(state)
    assert result["groundx_called"] is False
    assert result["groundx_results"] == []


@pytest.mark.asyncio
async def test_groundx_runs_in_groundx_mode():
    mock_client = MagicMock(search=AsyncMock(return_value=[{"text": "result"}]))
    with patch("backend.agent.nodes.groundx.groundx_client", mock_client):
        state = {"query": "search documents", "answer_mode": "groundx"}
        result = await groundx_retrieve_node(state)

    assert result["groundx_called"] is True
    assert result["groundx_global_search_allowed"] is True
    assert len(result["groundx_results"]) == 1
    mock_client.search.assert_called_once_with("search documents")


# ── OCR tests ──


@pytest.mark.asyncio
async def test_ocr_skipped_without_attachments_in_all_three_modes_chat_flow():
    for mode in ("groundx", "audio", "general"):
        state = {
            "query": "test",
            "answer_mode": mode,
            "attached_files": [],
        }
        result = await ocr_node(state, AsyncMock())
        assert result["ocr_called"] is False
        assert result["ocr_results"] == []


@pytest.mark.asyncio
async def test_general_mode_image_attachment_routes_directly_to_ocr(db_session):
    image_file = await crud.create_file(
        db_session,
        original_name="panel.png",
        file_type="image",
        disk_path="data/uploads/panel.png",
        size_bytes=10,
    )

    state = {
        "query": "Extract all visible written text from this image using OCR.",
        "answer_mode": "general",
        "attached_files": [image_file.id],
        "chat_id": "",
        "history": [],
        "routes": [],
        "thinking_steps": [],
        "query_category": "",
    }
    result = await router_node(state, session=db_session)

    assert result["routes"] == ["ocr"]
    assert result["retrieval_provider"] == "ocr"
    assert result["qdrant_called"] is False
    assert result["groundx_called"] is False
    assert _retrieval_route(result) == "ocr_only"


@pytest.mark.asyncio
async def test_groundx_mode_image_attachment_stays_groundx(db_session):
    image_file = await crud.create_file(
        db_session,
        original_name="panel.png",
        file_type="image",
        disk_path="data/uploads/panel.png",
        size_bytes=10,
    )

    state = {
        "query": "Use GroundX only",
        "answer_mode": "groundx",
        "attached_files": [image_file.id],
        "chat_id": "",
        "history": [],
        "routes": [],
        "thinking_steps": [],
        "query_category": "",
    }
    result = await router_node(state, session=db_session)

    assert result["routes"] == ["groundx"]
    assert result["retrieval_provider"] == "groundx"


@pytest.mark.asyncio
async def test_ocr_node_returns_cached_text_without_image_processor(db_session):
    image_file = await crud.create_file(
        db_session,
        original_name="label.png",
        file_type="image",
        disk_path="data/uploads/label.png",
        size_bytes=10,
    )
    await crud.create_ocr_result(
        db_session,
        file_id=image_file.id,
        extracted_text="cached label text from industrial equipment panel display",
        model_used="gemma4:12b",
    )

    with patch("backend.agent.nodes.ocr.image_processor._extract_text", new_callable=AsyncMock) as mock_extract:
        result = await ocr_node(
            {"query": "extract text", "answer_mode": "general", "attached_files": [image_file.id]},
            db_session,
        )

    assert result["ocr_called"] is True
    assert len(result["ocr_results"]) == 1
    assert result["ocr_results"][0]["content"] == "cached label text from industrial equipment panel display"
    mock_extract.assert_not_called()


@pytest.mark.asyncio
async def test_ocr_node_runs_on_demand_and_saves_result(db_session, tmp_path):
    image_path = tmp_path / "gauge.png"
    image_path.write_bytes(b"fake image bytes")
    image_file = await crud.create_file(
        db_session,
        original_name="gauge.png",
        file_type="image",
        disk_path=str(image_path),
        size_bytes=16,
    )

    with patch(
        "backend.agent.nodes.ocr.image_processor._extract_text",
        new=AsyncMock(return_value="OCR fallback text from gauge image showing pressure readings"),
    ) as mock_extract:
        result = await ocr_node(
            {"query": "extract text", "answer_mode": "general", "attached_files": [image_file.id]},
            db_session,
        )

    saved = await crud.get_ocr_result_by_file_id(db_session, image_file.id)
    assert result["ocr_called"] is True
    assert result["ocr_results"][0]["content"] == "OCR fallback text from gauge image showing pressure readings"
    assert saved is not None
    assert saved.extracted_text == "OCR fallback text from gauge image showing pressure readings"
    mock_extract.assert_awaited_once()


# ── No provider mixing tests ──


@pytest.mark.asyncio
async def test_no_provider_mixing_groundx_mode_never_calls_qdrant():
    with patch(
        "backend.agent.nodes.qdrant.qdrant_retriever"
    ) as mock_retriever:
        state = {"query": "test", "answer_mode": "groundx"}
        result = await qdrant_retrieve_node(state)

    mock_retriever.hybrid_query.assert_not_called()
    assert result["qdrant_called"] is False


@pytest.mark.asyncio
async def test_no_provider_mixing_audio_mode_never_calls_groundx():
    with patch(
        "backend.agent.nodes.groundx.groundx_client"
    ) as mock_client:
        state = {"query": "test", "answer_mode": "audio"}
        result = await groundx_retrieve_node(state)

    mock_client.search.assert_not_called()
    assert result["groundx_called"] is False
