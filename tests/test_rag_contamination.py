"""Regression tests for RAG contamination bug fixes.

Covers the 8 scenarios from the contamination-fix specification:
    1. English general question (no retrieval, no sources)
    2. Arabic general question (no retrieval, no sources)
    3. English industrial concept question (no retrieval)
    4. Arabic industrial concept question (no retrieval)
    5. Current attachment QA (retrieval scoped to attached files)
    6. Explicit manual question without scope (no global retrieval)
    7. History leakage regression (general question after RAG turn)
    8. History leakage after RAG over Arabic content
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.agent.nodes.context import (
    MIN_RELEVANCE_SCORE,
    _build_history_text,
    _sanitize_history_lines,
    context_synthesis_node,
)
from backend.agent.nodes.groundx import groundx_retrieve_node
from backend.agent.nodes.qdrant import qdrant_retrieve_node
from backend.agent.nodes.router import router_node
from backend.agent.query_classifier import QueryCategory, classify_query


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _blank_state(**overrides):
    base = {
        "query": "",
        "chat_id": "",
        "attached_files": [],
        "selected_scope": [],
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
        "model_name": None,
        "message_id": None,
        "qdrant_called": False,
        "groundx_called": False,
        "ocr_called": False,
        "retrieval_skipped_reason": "",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Scenario 1: English general question
# ---------------------------------------------------------------------------


class TestScenarioGeneralEnglish:
    def test_classifier_general_english(self):
        assert (
            classify_query("Who is Mohamed Hassanein Heikal?")
            == QueryCategory.GENERAL_CHAT
        )

    @pytest.mark.asyncio
    async def test_router_general_english_no_routes(self):
        state = _blank_state(query="Who is Mohamed Hassanein Heikal?")
        result = await router_node(state)
        assert result["routes"] == []
        assert result["query_category"] == "GENERAL_CHAT"

    @pytest.mark.asyncio
    async def test_qdrant_skipped_when_not_routed(self):
        state = _blank_state(
            query="Who is Mohamed Hassanein Heikal?",
            routes=[],
            query_category="GENERAL_CHAT",
        )
        out = await qdrant_retrieve_node(state)
        assert out["qdrant_results"] == []
        assert out["qdrant_called"] is False

    @pytest.mark.asyncio
    async def test_groundx_skipped_when_not_routed(self):
        state = _blank_state(
            query="Who is Mohamed Hassanein Heikal?",
            routes=[],
            query_category="GENERAL_CHAT",
        )
        out = await groundx_retrieve_node(state)
        assert out["groundx_results"] == []
        assert out["groundx_called"] is False

    @pytest.mark.asyncio
    async def test_context_prompt_mode_general(self):
        state = _blank_state(
            query="Who is Mohamed Hassanein Heikal?",
            query_category="GENERAL_CHAT",
            routes=[],
        )
        out = await context_synthesis_node(state)
        assert out["prompt_mode"] == "GENERAL"
        assert out["sources"] == []
        assert out["retrieved_context"] == ""


# ---------------------------------------------------------------------------
# Scenario 2: Arabic general question
# ---------------------------------------------------------------------------


class TestScenarioGeneralArabic:
    def test_classifier_general_arabic(self):
        assert classify_query("مين هو محمد حسنين هيكل؟") == QueryCategory.GENERAL_CHAT

    @pytest.mark.asyncio
    async def test_router_general_arabic_no_routes(self):
        state = _blank_state(query="مين هو محمد حسنين هيكل؟")
        result = await router_node(state)
        assert result["routes"] == []
        assert result["query_category"] == "GENERAL_CHAT"

    @pytest.mark.asyncio
    async def test_context_arabic_general_no_sources(self):
        state = _blank_state(
            query="مين هو محمد حسنين هيكل؟",
            query_category="GENERAL_CHAT",
            routes=[],
        )
        out = await context_synthesis_node(state)
        assert out["prompt_mode"] == "GENERAL"
        assert out["sources"] == []
        # No "النص المقدم" style history fed into prompt.
        assert out["history_text"] == ""


# ---------------------------------------------------------------------------
# Scenario 3: English industrial concept question
# ---------------------------------------------------------------------------


class TestScenarioIndustrialEnglish:
    def test_classifier_industrial_concept_difference(self):
        assert (
            classify_query("What is the difference between PLC and DCS?")
            == QueryCategory.INDUSTRIAL_KNOWLEDGE
        )

    def test_classifier_industrial_concept_what_is(self):
        assert classify_query("What is PLC?") == QueryCategory.INDUSTRIAL_KNOWLEDGE

    def test_classifier_industrial_concept_explain(self):
        assert classify_query("Explain OPC UA") == QueryCategory.INDUSTRIAL_KNOWLEDGE

    @pytest.mark.asyncio
    async def test_router_industrial_no_routes(self):
        state = _blank_state(query="What is the difference between PLC and DCS?")
        result = await router_node(state)
        assert result["routes"] == []
        assert result["query_category"] == "INDUSTRIAL_KNOWLEDGE"

    @pytest.mark.asyncio
    async def test_qdrant_refuses_industrial_category(self):
        # Even if something incorrectly routed qdrant, the node must refuse.
        state = _blank_state(
            query="What is PLC?",
            routes=["qdrant"],
            query_category="INDUSTRIAL_KNOWLEDGE",
        )
        out = await qdrant_retrieve_node(state)
        assert out["qdrant_results"] == []
        assert out["qdrant_called"] is False

    @pytest.mark.asyncio
    async def test_groundx_refuses_industrial_category(self):
        state = _blank_state(
            query="What is PLC?",
            routes=["groundx"],
            query_category="INDUSTRIAL_KNOWLEDGE",
        )
        out = await groundx_retrieve_node(state)
        assert out["groundx_results"] == []
        assert out["groundx_called"] is False

    @pytest.mark.asyncio
    async def test_context_industrial_general_mode(self):
        state = _blank_state(
            query="What is the difference between PLC and DCS?",
            query_category="INDUSTRIAL_KNOWLEDGE",
            routes=[],
        )
        out = await context_synthesis_node(state)
        assert out["prompt_mode"] == "INDUSTRIAL_GENERAL"
        assert out["sources"] == []
        assert out["retrieved_context"] == ""


# ---------------------------------------------------------------------------
# Scenario 4: Arabic industrial concept question
# ---------------------------------------------------------------------------


class TestScenarioIndustrialArabic:
    def test_classifier_arabic_difference(self):
        assert (
            classify_query("ما الفرق بين PLC و DCS؟")
            == QueryCategory.INDUSTRIAL_KNOWLEDGE
        )

    def test_classifier_arabic_explain(self):
        assert classify_query("اشرح معنى OPC UA") == QueryCategory.INDUSTRIAL_KNOWLEDGE

    @pytest.mark.asyncio
    async def test_router_arabic_industrial_no_routes(self):
        state = _blank_state(query="ما الفرق بين PLC و DCS؟")
        result = await router_node(state)
        assert result["routes"] == []
        assert result["query_category"] == "INDUSTRIAL_KNOWLEDGE"


# ---------------------------------------------------------------------------
# Scenario 5: Current attachment QA
# ---------------------------------------------------------------------------


class TestScenarioCurrentAttachment:
    def test_classifier_attachment_qa(self):
        result = classify_query(
            "Summarize the uploaded PDF",
            has_attached_files=True,
        )
        assert result == QueryCategory.CURRENT_ATTACHMENT_QA

    @pytest.mark.asyncio
    async def test_router_attachment_routes_to_qdrant_and_ocr(self):
        state = _blank_state(
            query="Summarize the uploaded PDF",
            attached_files=["file-1"],
        )
        result = await router_node(state)
        assert "qdrant" in result["routes"]
        assert "ocr" in result["routes"]

    @pytest.mark.asyncio
    async def test_qdrant_scopes_to_attached_files(self):
        captured = {}

        async def fake_hybrid_query(query_text, limit, file_id_filter=None):
            captured["filter"] = file_id_filter
            return []

        state = _blank_state(
            query="Summarize the uploaded PDF",
            attached_files=["file-1", "file-2"],
            routes=["qdrant"],
            query_category="CURRENT_ATTACHMENT_QA",
        )
        with patch(
            "backend.agent.nodes.qdrant.qdrant_retriever.hybrid_query",
            side_effect=fake_hybrid_query,
        ):
            out = await qdrant_retrieve_node(state)
        assert captured["filter"] == ["file-1", "file-2"]
        assert out["qdrant_called"] is True

    @pytest.mark.asyncio
    async def test_attachment_grounded_when_relevant_chunks_present(self):
        # Simulate a strong-relevance Qdrant chunk from an attached file.
        state = _blank_state(
            query="Summarize the uploaded PDF",
            query_category="CURRENT_ATTACHMENT_QA",
            routes=["qdrant"],
            attached_files=["file-1"],
            qdrant_results=[
                {
                    "id": "q-1",
                    "item_id": "q-1",
                    "content": "The pump P-101 vibrates above 7 mm/s.",
                    "text": "The pump P-101 vibrates above 7 mm/s.",
                    "source": "file-1#chunk-0",
                    "file_id": "file-1",
                    "file_name": "report.pdf",
                    "file_type": "pdf",
                    "chunk_index": 0,
                    "score": 0.85,
                    "retrieval_score": 0.85,
                    "payload": {},
                }
            ],
            ocr_results=[],
        )
        out = await context_synthesis_node(state)
        assert out["prompt_mode"] == "GROUNDED_RAG"
        assert out["sources"], "sources must be present for GROUNDED_RAG"
        assert out["retrieved_context"], "retrieved_context must be non-empty"


# ---------------------------------------------------------------------------
# Scenario 6: Explicit manual question without scope
# ---------------------------------------------------------------------------


class TestScenarioManualNoScope:
    def test_classifier_manual_without_scope(self):
        # No attached/selected -> RAG_REQUIRED, but downstream nodes will
        # refuse to perform global retrieval.
        assert (
            classify_query("What does the manual say about valve calibration?")
            == QueryCategory.RAG_REQUIRED
        )

    @pytest.mark.asyncio
    async def test_qdrant_refuses_when_no_scope(self):
        state = _blank_state(
            query="What does the manual say about valve calibration?",
            routes=["qdrant"],
            query_category="RAG_REQUIRED",
            attached_files=[],
            selected_scope=[],
        )
        out = await qdrant_retrieve_node(state)
        assert out["qdrant_results"] == []
        assert out["qdrant_called"] is False
        assert "no_scope" in out.get("retrieval_skipped_reason", "")

    @pytest.mark.asyncio
    async def test_groundx_refuses_when_no_scope(self):
        state = _blank_state(
            query="What does the manual say about valve calibration?",
            routes=["groundx"],
            query_category="RAG_REQUIRED",
            attached_files=[],
            selected_scope=[],
        )
        out = await groundx_retrieve_node(state)
        assert out["groundx_results"] == []
        assert out["groundx_called"] is False

    @pytest.mark.asyncio
    async def test_context_no_scope_gives_conservative_no_source(self):
        state = _blank_state(
            query="What does the manual say about valve calibration?",
            query_category="RAG_REQUIRED",
            routes=["qdrant"],
            qdrant_results=[],
            groundx_results=[],
            ocr_results=[],
        )
        out = await context_synthesis_node(state)
        assert out["prompt_mode"] == "CONSERVATIVE_NO_SOURCE"
        assert out["sources"] == []
        assert out["retrieved_context"] == ""


# ---------------------------------------------------------------------------
# Scenario 7: History leakage regression — "hi" after a RAG turn
# ---------------------------------------------------------------------------


class TestScenarioHistoryLeakage:
    def test_sanitize_strips_english_markers(self):
        msg = (
            "Based on the provided text, the pump runs at 1500 rpm.\n"
            "It is a centrifugal pump.\n"
            "Sources: report.pdf"
        )
        cleaned = _sanitize_history_lines(msg)
        assert "Based on" not in cleaned
        assert "Sources:" not in cleaned
        assert "centrifugal pump" in cleaned

    def test_sanitize_strips_arabic_markers(self):
        msg = (
            "بناءً على النص المقدم، المضخة تعمل بسرعة 1500 دورة في الدقيقة.\n"
            "هذه مضخة طاردة مركزية.\n"
            "المصادر: report.pdf"
        )
        cleaned = _sanitize_history_lines(msg)
        assert "النص المقدم" not in cleaned
        assert "المصادر" not in cleaned
        assert "طاردة مركزية" in cleaned

    def test_general_chat_history_is_empty(self):
        history = [
            {"role": "user", "content": "What does the report say about valve?"},
            {
                "role": "assistant",
                "content": "Based on the provided text, the valve is faulty.\nSources: report.pdf",
            },
        ]
        out = _build_history_text(history, "GENERAL", None)
        assert out == ""

    def test_industrial_general_history_sanitized(self):
        history = [
            {"role": "user", "content": "What does the report say?"},
            {
                "role": "assistant",
                "content": "According to the report, X is true.\nThe key takeaway is Y.\nSources: file.pdf",
            },
        ]
        out = _build_history_text(history, "INDUSTRIAL_GENERAL", None)
        assert "According to" not in out
        assert "Sources:" not in out
        assert "key takeaway is Y" in out

    @pytest.mark.asyncio
    async def test_general_after_rag_no_leakage(self):
        """A 'hi' after a grounded-RAG turn must not inherit source citations."""
        prior_assistant = (
            "Based on the provided text, the pump runs at 1500 rpm.\n"
            "Sources: pump_manual.pdf"
        )
        state = _blank_state(
            query="hi",
            query_category="GENERAL_CHAT",
            routes=[],
            history=[
                {"role": "user", "content": "What does the manual say?"},
                {"role": "assistant", "content": prior_assistant},
            ],
        )
        out = await context_synthesis_node(state)
        assert out["prompt_mode"] == "GENERAL"
        assert out["sources"] == []
        assert out["retrieved_context"] == ""
        # GENERAL mode strips history entirely to prevent ANY leakage.
        assert out["history_text"] == ""


# ---------------------------------------------------------------------------
# Scenario 8: Arabic general question after Arabic RAG turn
# ---------------------------------------------------------------------------


class TestScenarioHistoryLeakageArabic:
    @pytest.mark.asyncio
    async def test_arabic_general_after_rag_no_leakage(self):
        prior_assistant = (
            "بناءً على النص الذي قدمته، الموضوع يدور حول السياسة.\n"
            "المصادر: recording.mp3"
        )
        state = _blank_state(
            query="مين هو محمد حسنين هيكل؟",
            query_category="GENERAL_CHAT",
            routes=[],
            history=[
                {"role": "user", "content": "لخص التسجيل"},
                {"role": "assistant", "content": prior_assistant},
            ],
        )
        out = await context_synthesis_node(state)
        assert out["prompt_mode"] == "GENERAL"
        assert out["sources"] == []
        assert out["retrieved_context"] == ""
        assert out["history_text"] == ""


# ---------------------------------------------------------------------------
# Relevance gate
# ---------------------------------------------------------------------------


class TestRelevanceGate:
    def test_threshold_raised(self):
        assert MIN_RELEVANCE_SCORE >= 0.40, (
            "Relevance gate must be raised materially to prevent contamination "
            "(spec target: 0.45–0.55)."
        )

    @pytest.mark.asyncio
    async def test_weak_chunks_do_not_force_grounded_rag(self):
        # Qdrant returned a chunk but it is below the relevance gate.
        state = _blank_state(
            query="What does the manual say about valve calibration?",
            query_category="RAG_REQUIRED",
            routes=["qdrant"],
            qdrant_results=[
                {
                    "id": "q-1",
                    "item_id": "q-1",
                    "content": "Unrelated content about geopolitics.",
                    "text": "Unrelated content about geopolitics.",
                    "source": "old_file#chunk-0",
                    "file_id": "old_file",
                    "file_name": "old.pdf",
                    "file_type": "pdf",
                    "chunk_index": 0,
                    "score": 0.10,
                    "retrieval_score": 0.10,
                    "payload": {},
                }
            ],
        )
        out = await context_synthesis_node(state)
        # Weak chunk -> not GROUNDED_RAG, no sources, no retrieved context.
        assert out["prompt_mode"] != "GROUNDED_RAG"
        assert out["sources"] == []
        assert out["retrieved_context"] == ""
