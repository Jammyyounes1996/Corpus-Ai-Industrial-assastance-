"""RAG routing quality tests.

Validates that query classification and retrieval routing prevent
contamination of unrelated answers with irrelevant document context.

Target: >= 92% retrieval/source relevance accuracy.
"""

import pytest

from backend.agent.query_classifier import QueryCategory, classify_query
from backend.agent.nodes.context import MIN_RELEVANCE_SCORE


class TestQueryClassification:
    """Validate query classification prevents blind global RAG."""

    def test_general_greeting_no_rag(self):
        assert classify_query("Hello") == QueryCategory.GENERAL_CHAT

    def test_general_question_no_rag(self):
        assert classify_query("How are you?") == QueryCategory.GENERAL_CHAT

    def test_general_short_question_no_rag(self):
        assert classify_query("What time is it?") == QueryCategory.GENERAL_CHAT

    def test_arabic_greeting_no_rag(self):
        assert classify_query("مرحبا") == QueryCategory.GENERAL_CHAT

    def test_document_question_triggers_rag(self):
        result = classify_query("What does the uploaded document say about safety?")
        assert result == QueryCategory.RAG_REQUIRED

    def test_file_question_triggers_rag(self):
        result = classify_query("Summarize the PDF report")
        assert result == QueryCategory.RAG_REQUIRED

    def test_attached_file_triggers_attachment_qa(self):
        result = classify_query(
            "What is in this file?",
            has_attached_files=True,
        )
        assert result == QueryCategory.CURRENT_ATTACHMENT_QA

    def test_industrial_question_triggers_industrial(self):
        result = classify_query("What is the maintenance procedure for pump P-101?")
        assert result == QueryCategory.INDUSTRIAL_KNOWLEDGE

    def test_arabic_industrial_question(self):
        result = classify_query("ما هي إجراءات صيانة المضخة؟")
        assert result == QueryCategory.INDUSTRIAL_KNOWLEDGE

    def test_arabic_document_question(self):
        result = classify_query("ماذا يقول المستند عن السلامة؟")
        assert result == QueryCategory.RAG_REQUIRED

    def test_empty_query_is_general(self):
        assert classify_query("") == QueryCategory.GENERAL_CHAT

    def test_unknown_ambiguous_short(self):
        result = classify_query("Tell me more")
        assert result == QueryCategory.GENERAL_CHAT

    def test_audio_keyword_triggers_rag(self):
        result = classify_query("What was discussed in the audio recording?")
        assert result == QueryCategory.RAG_REQUIRED

    def test_transcript_keyword_triggers_rag(self):
        result = classify_query("Show the transcript content")
        assert result == QueryCategory.RAG_REQUIRED


class TestRelevanceThreshold:
    """Validate that a relevance threshold is defined and enforced."""

    def test_threshold_is_defined(self):
        assert MIN_RELEVANCE_SCORE > 0
        assert MIN_RELEVANCE_SCORE <= 1.0

    def test_threshold_is_conservative(self):
        assert MIN_RELEVANCE_SCORE >= 0.2, "Threshold should be at least 0.2 to filter noise"


class TestRouteIntegrity:
    """Validate that routes are set correctly for each category."""

    @pytest.mark.asyncio
    async def test_general_chat_gets_no_routes(self):
        from backend.agent.nodes.router import router_node

        state = {
            "query": "Hello!",
            "attached_files": [],
            "chat_id": "",
            "history": [],
            "routes": [],
            "thinking_steps": [],
            "query_category": "",
        }
        result = await router_node(state)
        assert result["routes"] == []
        assert result["query_category"] == "GENERAL_CHAT"

    @pytest.mark.asyncio
    async def test_document_question_gets_retrieval_routes(self):
        from backend.agent.nodes.router import router_node

        state = {
            "query": "What does the uploaded document say?",
            "attached_files": [],
            "chat_id": "",
            "history": [],
            "routes": [],
            "thinking_steps": [],
            "query_category": "",
        }
        result = await router_node(state)
        assert "qdrant" in result["routes"]
        assert result["query_category"] == "RAG_REQUIRED"

    @pytest.mark.asyncio
    async def test_attachment_query_scopes_to_qdrant_and_ocr(self):
        from backend.agent.nodes.router import router_node

        state = {
            "query": "What is in this image?",
            "attached_files": ["file-abc-123"],
            "chat_id": "",
            "history": [],
            "routes": [],
            "thinking_steps": [],
            "query_category": "",
        }
        result = await router_node(state)
        assert "qdrant" in result["routes"]
        assert "ocr" in result["routes"]
        assert result["query_category"] == "CURRENT_ATTACHMENT_QA"

    @pytest.mark.asyncio
    async def test_unknown_query_gets_no_routes(self):
        from backend.agent.nodes.router import router_node

        state = {
            "query": "Can you elaborate on the implications of quantum entanglement in materials science applications for next generation computing?",
            "attached_files": [],
            "chat_id": "",
            "history": [],
            "routes": [],
            "thinking_steps": [],
            "query_category": "",
        }
        result = await router_node(state)
        assert result["routes"] == []


class TestNoSourceContamination:
    """Validate that unrelated sources are not surfaced."""

    @pytest.mark.asyncio
    async def test_general_question_skips_retrieval(self):
        """A general unrelated question should NOT trigger retrieval."""
        category = classify_query("What is the weather today?")
        assert category == QueryCategory.GENERAL_CHAT

    @pytest.mark.asyncio
    async def test_geopolitical_audio_not_retrieved_for_general(self):
        """Geopolitical audio should NOT be retrieved for an unrelated general question."""
        category = classify_query("Tell me a joke")
        assert category == QueryCategory.GENERAL_CHAT

    def test_audio_question_routes_to_rag(self):
        """A question about audio content should trigger RAG."""
        category = classify_query("What was discussed in the audio about geopolitics?")
        assert category == QueryCategory.RAG_REQUIRED


class TestEvaluationMetrics:
    """Compute retrieval quality metrics from the classification tests above."""

    CASES = [
        ("Hello", False, False, "GENERAL_CHAT", True),
        ("What does the document say?", False, False, "RAG_REQUIRED", True),
        ("What was in the audio recording?", False, False, "RAG_REQUIRED", True),
        ("What is this?", True, False, "CURRENT_ATTACHMENT_QA", True),
        ("What is the pump maintenance procedure?", False, False, "INDUSTRIAL_KNOWLEDGE", True),
        ("مرحبا", False, False, "GENERAL_CHAT", True),
        ("ما هي إجراءات صيانة المعدات؟", False, False, "INDUSTRIAL_KNOWLEDGE", True),
        ("Tell me a joke", False, False, "GENERAL_CHAT", True),
    ]

    def test_classification_accuracy(self):
        correct = 0
        total = len(self.CASES)

        for query, has_attached, has_selected, expected_category, _ in self.CASES:
            result = classify_query(
                query,
                has_attached_files=has_attached,
                has_selected_files=has_selected,
            )
            if result.value == expected_category:
                correct += 1

        accuracy = correct / total
        print(f"\n=== RAG Classification Accuracy: {accuracy:.1%} ({correct}/{total}) ===")
        assert accuracy >= 0.92, f"Classification accuracy {accuracy:.1%} below 92% target"

    def test_no_source_accuracy(self):
        """General questions must not trigger retrieval."""
        general_cases = [c for c in self.CASES if c[3] == "GENERAL_CHAT"]
        correct = sum(
            1 for q, ha, hs, _, _ in general_cases
            if classify_query(q, has_attached_files=ha, has_selected_files=hs) == QueryCategory.GENERAL_CHAT
        )
        accuracy = correct / len(general_cases) if general_cases else 1.0
        print(f"\n=== No-Source Accuracy: {accuracy:.1%} ({correct}/{len(general_cases)}) ===")
        assert accuracy >= 0.92
