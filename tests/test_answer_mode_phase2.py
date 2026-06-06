from unittest.mock import patch

import pytest

from backend.agent.nodes.router import router_node


def _make_state(**overrides) -> dict:
    state = {
        "query": "test query",
        "chat_id": "test-chat-id",
        "attached_files": [],
        "selected_scope": [],
        "thinking_steps": [],
    }
    state.update(overrides)
    return state


@pytest.mark.asyncio
async def test_router_general_mode_returns_empty_routes():
    state = _make_state(answer_mode="general")
    result = await router_node(state)
    assert result["routes"] == []


@pytest.mark.asyncio
async def test_router_groundx_mode_returns_groundx_only():
    state = _make_state(answer_mode="groundx")
    result = await router_node(state)
    assert result["routes"] == ["groundx"]


@pytest.mark.asyncio
async def test_router_audio_mode_returns_qdrant_only():
    state = _make_state(answer_mode="audio")
    result = await router_node(state)
    assert result["routes"] == ["qdrant"]


@pytest.mark.asyncio
async def test_router_general_mode_sets_mode_decision():
    state = _make_state(answer_mode="general")
    result = await router_node(state)
    assert result["mode_decision"] == "general_no_retrieval"


@pytest.mark.asyncio
async def test_router_groundx_mode_sets_global_search_allowed():
    state = _make_state(answer_mode="groundx")
    result = await router_node(state)
    assert result["groundx_global_search_allowed"] is True


@pytest.mark.asyncio
async def test_router_audio_mode_sets_global_audio_allowed():
    state = _make_state(answer_mode="audio")
    result = await router_node(state)
    assert result["qdrant_global_audio_search_allowed"] is True


@pytest.mark.asyncio
async def test_router_does_not_call_classifier_in_explicit_modes():
    with patch("backend.agent.nodes.router.classify_query") as mock_classifier:
        for mode in ["general", "groundx", "audio"]:
            state = _make_state(answer_mode=mode)
            await router_node(state)
        mock_classifier.assert_not_called()
