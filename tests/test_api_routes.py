from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _stream_payload(attached_files: list[str] | None = None) -> dict:
    return {
        "query": "hello",
        "model_provider": "ollama",
        "model_name": "gemma4:latest",
        "attached_files": attached_files or [],
    }


def _make_empty_graph_factory():
    """Create a build_graph replacement that signals completion via the token_queue."""

    def factory(session, **kwargs):
        token_queue = kwargs.get("token_queue")

        class EmptyGraph:
            async def ainvoke(self, state, *args, **kw):
                if token_queue is not None:
                    await token_queue.put({"type": "done", "data": None})
                return {"answer": "", "sources": [], "thinking_steps": []}

        return EmptyGraph()

    return factory


def _make_broken_graph_factory():
    """Create a build_graph replacement that raises an error."""

    def factory(session, **kwargs):
        token_queue = kwargs.get("token_queue")

        class BrokenGraph:
            async def ainvoke(self, state, *args, **kw):
                raise RuntimeError("Traceback: C:\\internal\\path\\secret.py Error: boom")

        return BrokenGraph()

    return factory


@pytest.mark.asyncio
async def test_stream_chat_invalid_uuid(client):
    response = await client.post("/api/chat/not-a-uuid/stream", json=_stream_payload())
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_file_validation_uses_batch_query(client, monkeypatch):
    from backend.api.routes import chat as chat_module

    valid_chat_id = "11111111-1111-1111-1111-111111111111"
    file_ids = ["f1", "f2", "f3"]

    monkeypatch.setattr(
        chat_module.crud,
        "get_chat",
        AsyncMock(return_value=SimpleNamespace(id=valid_chat_id, model_provider="ollama", model_name="gemma4:latest")),
    )
    get_files_by_ids = AsyncMock(return_value=[SimpleNamespace(id=fid) for fid in file_ids])
    get_file = AsyncMock(return_value=None)
    monkeypatch.setattr(chat_module.crud, "get_files_by_ids", get_files_by_ids)
    monkeypatch.setattr(chat_module.crud, "get_file", get_file)
    monkeypatch.setattr(
        chat_module.crud,
        "create_message",
        AsyncMock(side_effect=[SimpleNamespace(id="u1"), SimpleNamespace(id="a1")]),
    )
    monkeypatch.setattr(chat_module.crud, "update_message_content", AsyncMock(return_value=None))

    monkeypatch.setattr(chat_module, "build_graph", _make_empty_graph_factory())

    response = await client.post(
        f"/api/chat/{valid_chat_id}/stream",
        json=_stream_payload(attached_files=file_ids),
    )

    assert response.status_code == 200
    get_files_by_ids.assert_awaited_once()
    get_file.assert_not_awaited()


@pytest.mark.asyncio
async def test_stream_error_not_leaked(client, monkeypatch):
    from backend.api.routes import chat as chat_module

    valid_chat_id = "22222222-2222-2222-2222-222222222222"

    monkeypatch.setattr(
        chat_module.crud,
        "get_chat",
        AsyncMock(return_value=SimpleNamespace(id=valid_chat_id, model_provider="ollama", model_name="gemma4:latest")),
    )
    monkeypatch.setattr(chat_module.crud, "get_files_by_ids", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        chat_module.crud,
        "create_message",
        AsyncMock(side_effect=[SimpleNamespace(id="u2"), SimpleNamespace(id="a2")]),
    )
    monkeypatch.setattr(chat_module.crud, "update_message_content", AsyncMock(return_value=None))

    monkeypatch.setattr(chat_module, "build_graph", _make_broken_graph_factory())

    response = await client.post(f"/api/chat/{valid_chat_id}/stream", json=_stream_payload())

    assert response.status_code == 200
    body = response.text
    assert "An internal error occurred. Please try again." in body
    assert "Traceback" not in body
    assert "Error:" not in body
    assert "C:\\" not in body


@pytest.mark.asyncio
async def test_history_not_fetched_in_route_handler(client, monkeypatch):
    from backend.api.routes import chat as chat_module

    valid_chat_id = "33333333-3333-3333-3333-333333333333"

    monkeypatch.setattr(
        chat_module.crud,
        "get_chat",
        AsyncMock(return_value=SimpleNamespace(id=valid_chat_id, model_provider="ollama", model_name="gemma4:latest")),
    )
    monkeypatch.setattr(chat_module.crud, "get_files_by_ids", AsyncMock(return_value=[]))
    get_messages = AsyncMock(return_value=[])
    monkeypatch.setattr(chat_module.crud, "get_messages", get_messages)
    monkeypatch.setattr(
        chat_module.crud,
        "create_message",
        AsyncMock(side_effect=[SimpleNamespace(id="u3"), SimpleNamespace(id="a3")]),
    )
    monkeypatch.setattr(chat_module.crud, "update_message_content", AsyncMock(return_value=None))

    monkeypatch.setattr(chat_module, "build_graph", _make_empty_graph_factory())

    response = await client.post(f"/api/chat/{valid_chat_id}/stream", json=_stream_payload())

    assert response.status_code == 200
    get_messages.assert_not_awaited()
