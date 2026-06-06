from unittest.mock import AsyncMock

import pytest

from backend.agent.nodes.context import context_synthesis_node
from backend.agent.nodes.groundx import groundx_retrieve_node
from backend.agent.nodes.router import router_node


def test_state_keys_exist():
    state = {
        "query": "test",
        "chat_id": "chat-1",
        "attached_files": [],
        "routes": [],
        "groundx_results": [],
        "qdrant_results": [],
        "ocr_results": [],
        "context": "",
        "sources": [],
        "answer": "",
        "thinking_steps": [],
        "query_category": "",
        "error": None,
        "history": [],
        "model_provider": "ollama",
        "model_name": "llama3",
        "message_id": "msg-1",
    }

    assert "groundx_results" in state
    assert "pdf_results" not in state
    assert "query_category" in state


@pytest.mark.asyncio
async def test_context_synthesis_return_keys(monkeypatch):
    from backend.agent.nodes import context as context_module

    monkeypatch.setattr(context_module.settings, "RERANKER_ENABLED", False, raising=False)
    monkeypatch.setattr(context_module.settings, "RERANKER_TOP_K", 5, raising=False)

    state = {
        "query": "What is in document?",
        "groundx_results": [{"a": 1, "content": "alpha", "source": "doc1", "score": 0.5}],
        "qdrant_results": [],
        "ocr_results": [],
        "history": [],
        "context": "",
        "sources": [],
        "thinking_steps": [],
    }

    result = await context_synthesis_node(state)

    assert "groundx_results" not in result
    assert "context" in result
    assert "sources" in result


@pytest.mark.asyncio
async def test_no_state_mutation_in_retrieval_nodes(monkeypatch):
    from backend.agent.nodes import groundx as groundx_module

    monkeypatch.setattr(groundx_module.groundx_client, "search", AsyncMock(return_value=[]))

    state = {
        "query": "test query",
        "thinking_steps": [],
    }

    result = await groundx_retrieve_node(state)

    assert "thinking_steps" not in result


@pytest.mark.asyncio
async def test_no_route_key_in_router_return():
    state = {
        "query": "test query",
        "attached_files": [],
        "chat_id": "chat-1",
        "history": [],
        "routes": [],
        "thinking_steps": [],
    }

    result = await router_node(state)

    assert "route" not in result
