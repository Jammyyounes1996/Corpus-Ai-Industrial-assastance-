from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.schemas.chat import StreamRequest


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _stream_payload(answer_mode: str | None = None, **overrides) -> dict:
    payload = {
        "query": "hello",
        "model_provider": "ollama",
        "model_name": "gemma4:latest",
        "attached_files": [],
    }
    if answer_mode is not None:
        payload["answer_mode"] = answer_mode
    payload.update(overrides)
    return payload


def _make_empty_graph_factory():
    def factory(session, **kwargs):
        token_queue = kwargs.get("token_queue")

        class EmptyGraph:
            async def ainvoke(self, state, *args, **kw):
                if token_queue is not None:
                    await token_queue.put({"type": "done", "data": None})
                return {
                    "answer": "",
                    "sources": [],
                    "thinking_steps": [],
                    "query_category": "",
                    "routes": [],
                    "qdrant_called": False,
                    "groundx_called": False,
                    "ocr_called": False,
                    "ocr_results": [],
                    "attached_files": [],
                    "selected_scope": [],
                    "retrieved_context": "",
                    "prompt_mode": "",
                    "history_text": "",
                    "retrieval_skipped_reason": "",
                    "answer_mode": state.get("answer_mode", "general"),
                    "retrieval_provider": state.get("retrieval_provider", ""),
                    "groundx_global_search_allowed": state.get("groundx_global_search_allowed", False),
                    "qdrant_global_audio_search_allowed": state.get("qdrant_global_audio_search_allowed", False),
                    "mode_decision": state.get("mode_decision", ""),
                }

        return EmptyGraph()

    return factory


def _setup_route_mocks(monkeypatch, chat_id="44444444-4444-4444-4444-444444444444"):
    from backend.api.routes import chat as chat_module

    monkeypatch.setattr(
        chat_module.crud,
        "get_chat",
        AsyncMock(return_value=SimpleNamespace(id=chat_id, model_provider="ollama", model_name="gemma4:latest")),
    )
    monkeypatch.setattr(chat_module.crud, "get_files_by_ids", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        chat_module.crud,
        "create_message",
        AsyncMock(side_effect=[SimpleNamespace(id="u4"), SimpleNamespace(id="a4")]),
    )
    monkeypatch.setattr(chat_module.crud, "update_message_content", AsyncMock(return_value=None))
    monkeypatch.setattr(chat_module, "build_graph", _make_empty_graph_factory())


def test_stream_request_defaults_answer_mode_to_general():
    req = StreamRequest(query="hello")
    assert req.answer_mode == "general"


def test_stream_request_rejects_invalid_answer_mode():
    import pydantic

    with pytest.raises(pydantic.ValidationError) as exc_info:
        StreamRequest(query="hello", answer_mode="auto")
    assert exc_info.value.error_count() == 1
    errors = exc_info.value.errors()
    assert errors[0]["type"] == "literal_error"


@pytest.mark.parametrize("mode", ["groundx", "audio", "general"])
def test_stream_request_accepts_each_valid_mode(mode):
    req = StreamRequest(query="hello", answer_mode=mode)
    assert req.answer_mode == mode


@pytest.mark.asyncio
async def test_rag_trace_includes_answer_mode_fields(client, monkeypatch):
    import json

    from backend.api.routes import chat as chat_module

    captured_log_args = {}

    original_info = chat_module.logger.info

    def capture_info(fmt, *args, **kwargs):
        if fmt.startswith("RAG_TRACE"):
            captured_log_args["fmt"] = fmt
            captured_log_args["args"] = args
        return original_info(fmt, *args, **kwargs)

    monkeypatch.setattr(chat_module.logger, "info", capture_info)

    chat_id = "55555555-5555-5555-5555-555555555555"
    _setup_route_mocks(monkeypatch, chat_id=chat_id)

    response = await client.post(
        f"/api/chat/{chat_id}/stream",
        json=_stream_payload(answer_mode="groundx"),
    )

    assert response.status_code == 200
    assert "RAG_TRACE" in captured_log_args.get("fmt", "")
    fmt = captured_log_args["fmt"]
    assert "answer_mode={}" in fmt
    assert "retrieval_provider={}" in fmt
    assert "groundx_global_search_allowed={}" in fmt
    assert "qdrant_global_audio_search_allowed={}" in fmt
    assert "mode_decision={!r}" in fmt

    args = captured_log_args["args"]
    assert "groundx" in args
