from __future__ import annotations

import asyncio

import pytest

from backend.agent.nodes.answer import answer_node
from backend.agent.nodes.router import router_node
from backend.agent.nodes.web_search import web_search_node
from backend.core.web_search.provider import WebSearchProvider


def _base_state(query: str) -> dict:
    return {
        "query": query,
        "chat_id": "chat-1",
        "attached_files": [],
        "routes": [],
        "groundx_results": [],
        "groundx_search_text": "",
        "qdrant_results": [],
        "ocr_results": [],
        "context": "",
        "retrieved_context": "",
        "history_text": "",
        "prompt_mode": "GENERAL",
        "sources": [],
        "answer": "",
        "thinking_steps": [],
        "query_category": "",
        "error": None,
        "history": [],
        "model_provider": "ollama",
        "model_name": "test-model",
        "message_id": "msg-1",
        "selected_scope": [],
        "qdrant_called": False,
        "groundx_called": False,
        "ocr_called": False,
        "retrieval_skipped_reason": "",
        "answer_mode": "general",
        "retrieval_provider": "none",
        "groundx_global_search_allowed": False,
        "qdrant_global_audio_search_allowed": False,
        "mode_decision": "",
        "no_match_message_type": "",
        "task_type": "",
        "search_required": False,
        "search_reason": None,
        "search_used": False,
        "search_error": None,
        "web_results": [],
        "web_sources": [],
    }


@pytest.mark.asyncio
async def test_router_marks_search_required_for_latest_query() -> None:
    state = _base_state("double check latest OpenAI API changes and give me sources")
    result = await router_node(state)
    assert result["search_required"] is True
    assert result["search_reason"]


@pytest.mark.asyncio
async def test_router_marks_search_not_required_for_stable_general_question() -> None:
    state = _base_state("مين هو طه حسين؟")
    result = await router_node(state)
    assert result["search_required"] is False


@pytest.mark.asyncio
async def test_web_search_disabled_fails_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.core.web_search.provider.get_settings", lambda: type("S", (), {
        "WEB_SEARCH_ENABLED": False,
        "WEB_SEARCH_PROVIDER": "brave",
        "WEB_SEARCH_API_KEY": "",
        "WEB_SEARCH_MAX_RESULTS": 5,
        "WEB_SEARCH_TIMEOUT_SECONDS": 5,
    })())
    state = _base_state("latest OPC UA standard version")
    state["search_required"] = True
    result = await web_search_node(state)
    assert result["search_used"] is False
    assert "configured" in result["search_error"]


@pytest.mark.asyncio
async def test_tavily_provider_normalizes_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.core.web_search.provider.get_settings", lambda: type("S", (), {
        "WEB_SEARCH_ENABLED": True,
        "WEB_SEARCH_PROVIDER": "tavily",
        "WEB_SEARCH_API_KEY": "test-key",
        "WEB_SEARCH_MAX_RESULTS": 5,
        "WEB_SEARCH_TIMEOUT_SECONDS": 10,
    })())

    captured: dict = {}

    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "results": [
                    {
                        "title": "OPC UA Overview",
                        "url": "https://reference.opcfoundation.org/overview",
                        "content": "Current OPC UA overview and references.",
                        "published_date": "2025-02-10",
                    }
                ]
            }

    class DummyClient:
        def __init__(self, timeout: float) -> None:
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url: str, *, headers: dict, json: dict):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return DummyResponse()

    monkeypatch.setattr("backend.core.web_search.provider.httpx.AsyncClient", DummyClient)
    provider = WebSearchProvider()
    results = await provider.search("latest OPC UA standard")
    assert provider.provider_name == "tavily"
    assert captured["url"] == "https://api.tavily.com/search"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["max_results"] == 5
    assert results == [
        {
            "title": "OPC UA Overview",
            "url": "https://reference.opcfoundation.org/overview",
            "snippet": "Current OPC UA overview and references.",
            "source": "reference.opcfoundation.org",
            "published_date": "2025-02-10",
        }
    ]


@pytest.mark.asyncio
async def test_web_search_node_uses_normalized_results(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyProvider:
        provider_name = "tavily"

        def is_configured(self) -> bool:
            return True

        async def search(self, query: str) -> list[dict]:
            return [
                {
                    "title": "OPC Foundation",
                    "url": "https://opcfoundation.org/spec",
                    "snippet": "Latest spec details",
                    "source": "opcfoundation.org",
                    "published_date": "2025-01-01",
                }
            ]

    monkeypatch.setattr("backend.agent.nodes.web_search.WebSearchProvider", DummyProvider)
    state = _base_state("double check أحدث إصدار من معيار OPC UA واديني المصادر")
    state["search_required"] = True
    result = await web_search_node(state)
    assert result["search_used"] is True
    assert result["web_results"][0]["url"] == "https://opcfoundation.org/spec"
    assert result["web_sources"][0]["file_name"] == "OPC Foundation"


@pytest.mark.asyncio
async def test_web_search_emits_workflow_events(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyProvider:
        provider_name = "tavily"

        def is_configured(self) -> bool:
            return True

        async def search(self, query: str) -> list[dict]:
            return []

    monkeypatch.setattr("backend.agent.nodes.web_search.WebSearchProvider", DummyProvider)
    queue: asyncio.Queue = asyncio.Queue()
    state = _base_state("latest API version")
    state["search_required"] = True
    result = await web_search_node(state, token_queue=queue)
    first = await queue.get()
    second = await queue.get()
    assert first["data"]["data"]["node"] == "WEB_SEARCH"
    assert first["data"]["data"]["provider"] == "tavily"
    assert second["data"]["data"]["node"] == "WEB_SEARCH"
    assert result["search_used"] is False


@pytest.mark.asyncio
async def test_tavily_missing_key_fails_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.core.web_search.provider.get_settings", lambda: type("S", (), {
        "WEB_SEARCH_ENABLED": True,
        "WEB_SEARCH_PROVIDER": "tavily",
        "WEB_SEARCH_API_KEY": "",
        "WEB_SEARCH_MAX_RESULTS": 5,
        "WEB_SEARCH_TIMEOUT_SECONDS": 10,
    })())
    state = _base_state("what is the latest version of Node.js? cite sources")
    state["search_required"] = True
    result = await web_search_node(state)
    assert result["search_used"] is False
    assert result["web_results"] == []
    assert "configured" in result["search_error"]


@pytest.mark.asyncio
async def test_unsupported_provider_fails_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.core.web_search.provider.get_settings", lambda: type("S", (), {
        "WEB_SEARCH_ENABLED": True,
        "WEB_SEARCH_PROVIDER": "duckduckgo",
        "WEB_SEARCH_API_KEY": "test-key",
        "WEB_SEARCH_MAX_RESULTS": 5,
        "WEB_SEARCH_TIMEOUT_SECONDS": 10,
    })())
    provider = WebSearchProvider()
    with pytest.raises(ValueError, match="Unsupported web search provider: duckduckgo"):
        await provider.search("latest OPC UA standard")


@pytest.mark.asyncio
async def test_brave_provider_still_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.core.web_search.provider.get_settings", lambda: type("S", (), {
        "WEB_SEARCH_ENABLED": True,
        "WEB_SEARCH_PROVIDER": "brave",
        "WEB_SEARCH_API_KEY": "brave-key",
        "WEB_SEARCH_MAX_RESULTS": 3,
        "WEB_SEARCH_TIMEOUT_SECONDS": 7,
    })())

    captured: dict = {}

    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "web": {
                    "results": [
                        {
                            "title": "Node.js Releases",
                            "url": "https://nodejs.org/en/about/previous-releases",
                            "description": "Official Node.js release schedule.",
                        }
                    ]
                }
            }

    class DummyClient:
        def __init__(self, timeout: float) -> None:
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url: str, *, headers: dict, params: dict):
            captured["url"] = url
            captured["headers"] = headers
            captured["params"] = params
            return DummyResponse()

    monkeypatch.setattr("backend.core.web_search.provider.httpx.AsyncClient", DummyClient)
    provider = WebSearchProvider()
    results = await provider.search("latest Node.js version")
    assert provider.provider_name == "brave"
    assert captured["url"] == "https://api.search.brave.com/res/v1/web/search"
    assert captured["headers"]["X-Subscription-Token"] == "brave-key"
    assert captured["params"]["count"] == 3
    assert results[0]["source"] == "nodejs.org"


@pytest.mark.asyncio
async def test_answer_includes_sources_when_web_search_used(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyClient:
        async def chat_stream(self, **kwargs):
            yield {"content": "تم التحقق من مصادر حديثة\n\n## الإجابة\n[OPC Foundation](https://opcfoundation.org/spec)"}
            yield {
                "done": True,
                "eval_count": 120,
                "prompt_eval_count": 80,
                "total_duration": 2_000_000,
                "done_reason": "stop",
            }

        async def generate_stream(self, **kwargs):
            if False:
                yield kwargs

    monkeypatch.setattr("backend.agent.nodes.answer.OllamaClient", lambda: DummyClient())
    state = _base_state("double check أحدث إصدار من معيار OPC UA واديني المصادر")
    state["search_used"] = True
    state["search_required"] = True
    state["web_results"] = [
        {
            "title": "OPC Foundation",
            "url": "https://opcfoundation.org/spec",
            "snippet": "Latest spec details",
            "source": "opcfoundation.org",
            "published_date": "2025-01-01",
        }
    ]
    state["sources"] = [
        {
            "file_id": "https://opcfoundation.org/spec",
            "file_name": "OPC Foundation",
            "file_type": "text",
            "chunk_index": 0,
            "score": 1.0,
            "excerpt": "Latest spec details",
        }
    ]
    queue: asyncio.Queue = asyncio.Queue()
    result = await answer_node(state, token_queue=queue)
    assert "OPC Foundation" in result["answer"]
    emitted = []
    while not queue.empty():
        emitted.append((await queue.get())["type"])
    assert "sources" in emitted
