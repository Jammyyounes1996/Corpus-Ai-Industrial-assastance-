"""Regression tests that exercise the REAL agent graph end-to-end.

These tests target the runtime contamination bug where:
- prior assistant turns referencing uploaded audio leaked into general questions
- INDUSTRIAL_KNOWLEDGE queries returned "Based on the text provided..." refusals
- UNKNOWN/long Arabic queries pulled unrelated retrieval into context

They mock OllamaClient / qdrant_retriever / groundx_client at module boundaries so the
real router/context/answer nodes execute, the real graph routing edges fire, and the
real prompt_mode selection runs.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.agent.graph import build_graph
from backend.agent.state import AgentState


def _make_state(query: str, **overrides: Any) -> AgentState:
    base: dict[str, Any] = {
        "query": query,
        "chat_id": "",
        "attached_files": [],
        "routes": [],
        "groundx_results": [],
        "qdrant_results": [],
        "ocr_results": [],
        "context": "",
        "retrieved_context": "",
        "history_text": "",
        "prompt_mode": "",
        "sources": [],
        "answer": "",
        "thinking_steps": [],
        "query_category": "",
        "error": None,
        "history": [],
        "model_provider": "ollama",
        "model_name": "llama3.1",
        "message_id": None,
    }
    base.update(overrides)
    return base  # type: ignore[return-value]


class _FakeAsyncTokenStream:
    """Async generator that yields a fixed answer text token by token."""

    def __init__(self, text: str) -> None:
        self._tokens = [text] if text else []

    def __aiter__(self) -> "_FakeAsyncTokenStream":
        self._iter = iter(self._tokens)
        return self

    async def __anext__(self) -> str:
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


def _patch_ollama(answer_text: str = "MOCK_LLM_ANSWER") -> Any:
    """Patch the OllamaClient used inside answer_node so no real HTTP happens."""
    mock_client = MagicMock()
    mock_client.generate_stream = MagicMock(return_value=_FakeAsyncTokenStream(answer_text))
    return patch("backend.agent.nodes.answer.OllamaClient", return_value=mock_client)


def _patch_qdrant_empty() -> Any:
    return patch(
        "backend.agent.nodes.qdrant.qdrant_retriever",
        MagicMock(hybrid_query=AsyncMock(return_value=[])),
    )


def _patch_qdrant_geopolitics() -> Any:
    """Qdrant returns geopolitical-audio chunks with low scores below threshold."""
    chunks = [
        {
            "id": f"chunk-{i}",
            "score": 0.10,
            "payload": {
                "chunk_text": "audio transcript about geopolitics and elections " * 3,
                "file_id": "audio-001",
                "original_name": "audio_geopolitics.mp3",
                "file_type": "audio",
                "chunk_index": i,
            },
        }
        for i in range(3)
    ]
    return patch(
        "backend.agent.nodes.qdrant.qdrant_retriever",
        MagicMock(hybrid_query=AsyncMock(return_value=chunks)),
    )


def _patch_qdrant_relevant_audio() -> Any:
    """Qdrant returns audio chunks with high relevance to an explicit audio query."""
    chunks = [
        {
            "id": f"chunk-{i}",
            "score": 0.85,
            "payload": {
                "chunk_text": "Geopolitical analysis: regional tensions and trade impacts.",
                "file_id": "audio-001",
                "original_name": "audio_geopolitics.mp3",
                "file_type": "audio",
                "chunk_index": i,
            },
        }
        for i in range(2)
    ]
    return patch(
        "backend.agent.nodes.qdrant.qdrant_retriever",
        MagicMock(hybrid_query=AsyncMock(return_value=chunks)),
    )


def _patch_groundx_empty() -> Any:
    return patch(
        "backend.agent.nodes.groundx.groundx_client",
        MagicMock(search=AsyncMock(return_value=[])),
    )


def _patch_reranker_passthrough() -> Any:
    async def _identity(_query: str, results: list[dict], top_k: int) -> list[dict]:
        return results[:top_k]

    return patch(
        "backend.agent.nodes.context.reranker",
        MagicMock(rerank=AsyncMock(side_effect=_identity)),
    )


async def _run_graph(state: AgentState) -> dict[str, Any]:
    queue: asyncio.Queue = asyncio.Queue()
    graph = build_graph(session=None, token_queue=queue)
    return await graph.ainvoke(state, config={"configurable": {"session": None}})


@pytest.mark.asyncio
async def test_arabic_general_question_no_rag_no_doc_phrasing():
    """مين هو محمد حسنين هيكل؟ — must be GENERAL_CHAT with no retrieval and no doc citation."""
    state = _make_state("مين هو محمد حسنين هيكل؟")
    with (
        _patch_ollama("محمد حسنين هيكل صحفي وكاتب مصري شهير.") as _,
        _patch_qdrant_geopolitics() as qmock,
        _patch_groundx_empty() as gmock,
        _patch_reranker_passthrough(),
    ):
        result = await _run_graph(state)

    assert result["query_category"] == "GENERAL_CHAT"
    assert result["routes"] == []
    assert result["qdrant_results"] == []
    assert result["groundx_results"] == []
    assert result["retrieved_context"] == ""
    assert result["prompt_mode"] == "GENERAL"
    answer = result["answer"]
    for banned in (
        "Based on the text provided",
        "Based on the provided text",
        "Based on the documents",
        "النص الذي قدمته",
        "بناءً على النصوص المقدمة",
    ):
        assert banned not in answer


@pytest.mark.asyncio
async def test_english_industrial_question_falls_back_to_general_knowledge():
    """PLC vs DCS — INDUSTRIAL_KNOWLEDGE category, no retrieval at all.

    Under the contamination-fix architecture, industrial-concept questions
    never route to qdrant/groundx; they go straight to INDUSTRIAL_GENERAL.
    """
    state = _make_state("What is the difference between PLC and DCS?")
    with (
        _patch_ollama("PLC controls discrete logic; DCS coordinates distributed processes.") as _,
        _patch_qdrant_geopolitics(),
        _patch_groundx_empty(),
        _patch_reranker_passthrough(),
    ):
        result = await _run_graph(state)

    assert result["query_category"] == "INDUSTRIAL_KNOWLEDGE"
    # New architecture: no retrieval routes for industrial-concept questions.
    assert result["routes"] == []
    assert result["qdrant_results"] == []
    assert result["groundx_results"] == []
    assert result["retrieved_context"] == ""
    assert result["sources"] == []
    assert result["prompt_mode"] == "INDUSTRIAL_GENERAL"
    answer = result["answer"]
    assert "Based on the text provided" not in answer
    assert "Based on the documents" not in answer


@pytest.mark.asyncio
async def test_no_source_machine_question_uses_conservative_no_source():
    """ماكينة غير موجودة عندك — must be doc-flavored, no geopolitical leak, conservative."""
    state = _make_state("ما هي تعليمات التشغيل الخاصة بماكينة غير موجودة عندك؟")
    with (
        _patch_ollama("لا تتوفر لديّ معلومات موثّقة كافية للإجابة على هذا السؤال.") as _,
        _patch_qdrant_geopolitics(),
        _patch_groundx_empty(),
        _patch_reranker_passthrough(),
    ):
        result = await _run_graph(state)

    assert result["query_category"] in (
        "RAG_REQUIRED",
        "FILE_QA",
        "INDUSTRIAL_KNOWLEDGE",
    )
    # geopolitical noise must be filtered out by 0.25 threshold.
    assert result["retrieved_context"] == ""
    assert result["prompt_mode"] in ("CONSERVATIVE_NO_SOURCE", "INDUSTRIAL_GENERAL")
    # No leaked geopolitical sources at all if scores below threshold.
    sources = result.get("sources") or []
    leaked = [s for s in sources if "geopolit" in (s.get("file_name", "") or "").lower()]
    assert not leaked


@pytest.mark.asyncio
async def test_explicit_audio_question_does_retrieval_and_uses_sources():
    """Explicit audio request with an explicit attachment — hits retrieval and surfaces audio source.

    Under the contamination-fix architecture, retrieval requires explicit
    scope: either attached_files for this request or selected_scope. A pure
    "talk about the audio file" query with NO scope is no longer allowed
    to global-search; the caller must attach the audio file.
    """
    state = _make_state(
        "لخصلي الملف الصوتي اللي بيتكلم عن الأحداث الجيوسياسية",
        attached_files=["audio-001"],
    )
    with (
        _patch_ollama("ملخص: الملف الصوتي يناقش التوترات الإقليمية وآثارها التجارية.") as _,
        _patch_qdrant_relevant_audio(),
        _patch_groundx_empty(),
        _patch_reranker_passthrough(),
        patch(
            "backend.agent.nodes.ocr.get_ocr_result_by_file_id",
            AsyncMock(return_value=None),
        ),
    ):
        result = await _run_graph(state)

    assert result["query_category"] == "CURRENT_ATTACHMENT_QA"
    assert "qdrant" in result["routes"]
    assert result["retrieved_context"] != ""
    assert result["prompt_mode"] == "GROUNDED_RAG"
    sources = result.get("sources") or []
    assert sources, "expected at least one source for explicit audio query"
    assert any("audio" in (s.get("file_name", "") or "").lower() for s in sources)


@pytest.mark.asyncio
async def test_general_after_audio_does_not_leak_audio_into_context():
    """After an audio Q/A turn, a general question must not pick up audio context."""
    history = [
        {"role": "user", "content": "لخصلي الملف الصوتي عن الأحداث الجيوسياسية"},
        {
            "role": "assistant",
            "content": (
                "الملف الصوتي يناقش التوترات الإقليمية وآثارها التجارية. "
                "Sources: audio_geopolitics.mp3"
            ),
        },
    ]
    state = _make_state("مين هو محمد حسنين هيكل؟", history=history)
    with (
        _patch_ollama("محمد حسنين هيكل صحفي مصري بارز.") as _,
        _patch_qdrant_geopolitics(),
        _patch_groundx_empty(),
        _patch_reranker_passthrough(),
    ):
        result = await _run_graph(state)

    assert result["query_category"] == "GENERAL_CHAT"
    assert result["routes"] == []
    assert result["qdrant_results"] == []
    assert result["groundx_results"] == []
    assert result["retrieved_context"] == ""
    assert result["prompt_mode"] == "GENERAL"
    # Under the contamination-fix architecture, GENERAL mode strips history
    # entirely so prior "Sources: audio_geopolitics.mp3" cannot leak in.
    assert result["history_text"] == ""
    assert "audio_geopolitics" not in result["retrieved_context"]
    assert "audio_geopolitics" not in result["history_text"]
