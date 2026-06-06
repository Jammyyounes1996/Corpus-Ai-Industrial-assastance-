from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.agent.nodes.qdrant import qdrant_retrieve_node
from backend.agent.nodes.groundx import groundx_retrieve_node
from backend.agent.nodes.ocr import ocr_node


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
async def test_ocr_skipped_in_all_three_modes_chat_flow():
    session = AsyncMock()
    for mode in ("groundx", "audio", "general"):
        state = {
            "query": "test",
            "answer_mode": mode,
            "attached_files": ["file-1"],
        }
        result = await ocr_node(state, session)
        assert result["ocr_called"] is False
        assert result["ocr_results"] == []


@pytest.mark.asyncio
async def test_ocr_image_ingestion_pipeline_still_runs():
    mock_ocr = AsyncMock(
        return_value=SimpleNamespace(extracted_text="extracted text from image")
    )
    with patch("backend.agent.nodes.ocr.get_ocr_result_by_file_id", mock_ocr):
        state = {"query": "describe this image", "attached_files": ["img-001"]}
        session = AsyncMock()
        result = await ocr_node(state, session)

    assert result["ocr_called"] is True
    assert len(result["ocr_results"]) == 1
    assert result["ocr_results"][0]["content"] == "extracted text from image"


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
