import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.agent.nodes.context import context_synthesis_node
from backend.agent.nodes.answer import answer_node


def _base_state(**overrides):
    state = {
        "query": "test query",
        "chat_id": "chat-1",
        "message_id": "msg-1",
        "attached_files": [],
        "routes": [],
        "groundx_results": [],
        "qdrant_results": [],
        "ocr_results": [],
        "history": [],
        "thinking_steps": [],
        "qdrant_called": False,
        "groundx_called": False,
        "ocr_called": False,
        "retrieval_skipped_reason": "",
        "selected_scope": [],
    }
    state.update(overrides)
    return state


class _AsyncGen:
    def __init__(self, tokens):
        self._tokens = list(tokens)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._tokens:
            raise StopAsyncIteration
        return self._tokens.pop(0)


def _mock_settings():
    s = MagicMock()
    s.RERANKER_ENABLED = False
    s.RERANKER_TOP_K = 10
    return s


def _drain_queue(queue):
    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    return events


def _event_types(events):
    return [event.get("type") for event in events]


# ── context.py: general mode ──


@pytest.mark.asyncio
async def test_context_general_mode_sets_prompt_mode_GENERAL():
    state = _base_state(answer_mode="general")
    result = await context_synthesis_node(state)
    assert result["prompt_mode"] == "GENERAL"


@pytest.mark.asyncio
async def test_context_general_mode_clears_sources():
    state = _base_state(
        answer_mode="general",
        qdrant_results=[{"content": "leak", "score": 0.9, "file_type": "pdf"}],
    )
    result = await context_synthesis_node(state)
    assert result["sources"] == []
    assert result["retrieved_context"] == ""
    assert result["no_match_message_type"] == ""


# ── context.py: groundx mode ──


@pytest.mark.asyncio
async def test_context_groundx_match_sets_GROUNDED_RAG():
    groundx_chunks = [
        {
            "content": "relevant pdf text",
            "score": 0.85,
            "source": "doc.pdf",
            "file_id": "f1",
            "file_name": "doc.pdf",
            "file_type": "pdf",
            "chunk_index": 0,
        },
    ]
    state = _base_state(answer_mode="groundx", groundx_results=groundx_chunks)
    result = await context_synthesis_node(state)
    assert result["prompt_mode"] == "GROUNDED_RAG"
    assert len(result["sources"]) >= 1
    assert result["no_match_message_type"] == ""


@pytest.mark.asyncio
async def test_context_groundx_no_match_sets_CONSERVATIVE_NO_SOURCE():
    state = _base_state(answer_mode="groundx", groundx_results=[])
    result = await context_synthesis_node(state)
    assert result["prompt_mode"] == "CONSERVATIVE_NO_SOURCE"


@pytest.mark.asyncio
async def test_context_groundx_no_match_sets_msg_type_groundx_no_match():
    state = _base_state(answer_mode="groundx", groundx_results=[])
    result = await context_synthesis_node(state)
    assert result["no_match_message_type"] == "groundx_no_match"


# ── context.py: audio mode ──


@pytest.mark.asyncio
async def test_context_audio_match_sets_GROUNDED_RAG():
    audio_chunks = [
        {
            "content": "audio transcript",
            "score": 0.80,
            "retrieval_score": 0.80,
            "source": "meeting.mp3",
            "file_id": "a1",
            "file_name": "meeting.mp3",
            "file_type": "audio",
            "chunk_index": 0,
        },
    ]
    state = _base_state(answer_mode="audio", qdrant_results=audio_chunks)
    result = await context_synthesis_node(state)
    assert result["prompt_mode"] == "GROUNDED_RAG"
    assert len(result["sources"]) >= 1


@pytest.mark.asyncio
async def test_context_audio_no_match_sets_msg_type_audio_no_match():
    state = _base_state(answer_mode="audio", qdrant_results=[])
    result = await context_synthesis_node(state)
    assert result["prompt_mode"] == "CONSERVATIVE_NO_SOURCE"
    assert result["no_match_message_type"] == "audio_no_match"


@pytest.mark.asyncio
async def test_context_no_provider_mixing():
    groundx_chunks = [
        {
            "content": "groundx stuff",
            "score": 0.90,
            "source": "gx.pdf",
            "file_id": "gx1",
            "file_name": "gx.pdf",
            "file_type": "pdf",
            "chunk_index": 0,
        },
    ]
    state = _base_state(answer_mode="audio", groundx_results=groundx_chunks)
    result = await context_synthesis_node(state)
    assert result["prompt_mode"] == "CONSERVATIVE_NO_SOURCE"
    assert all(
        s.get("type") != "groundx" for s in result.get("sources", [])
    )


# ── answer.py: no-match fast path ──


@pytest.mark.asyncio
async def test_answer_groundx_no_match_returns_exact_arabic_message():
    state = _base_state(
        prompt_mode="CONSERVATIVE_NO_SOURCE",
        no_match_message_type="groundx_no_match",
    )
    result = await answer_node(state)
    assert result["answer"] == "لا توجد معلومات كافية في GroundX للإجابة على هذا السؤال."


@pytest.mark.asyncio
async def test_answer_groundx_no_match_does_not_call_llm():
    with patch("backend.agent.nodes.answer.OllamaClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.generate_stream = AsyncMock()
        mock_client_cls.return_value = mock_client
        state = _base_state(
            prompt_mode="CONSERVATIVE_NO_SOURCE",
            no_match_message_type="groundx_no_match",
        )
        await answer_node(state)
        mock_client.generate_stream.assert_not_called()


@pytest.mark.asyncio
async def test_answer_audio_no_match_returns_exact_arabic_message():
    state = _base_state(
        prompt_mode="CONSERVATIVE_NO_SOURCE",
        no_match_message_type="audio_no_match",
    )
    result = await answer_node(state)
    assert result["answer"] == "لا توجد معلومات كافية في التسجيلات الصوتية للإجابة على هذا السؤال."


@pytest.mark.asyncio
async def test_answer_audio_no_match_does_not_call_llm():
    with patch("backend.agent.nodes.answer.OllamaClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.generate_stream = AsyncMock()
        mock_client_cls.return_value = mock_client
        state = _base_state(
            prompt_mode="CONSERVATIVE_NO_SOURCE",
            no_match_message_type="audio_no_match",
        )
        await answer_node(state)
        mock_client.generate_stream.assert_not_called()


@pytest.mark.asyncio
async def test_answer_general_mode_calls_llm_without_context():
    mock_client = MagicMock()
    mock_client.generate_stream = MagicMock(return_value=_AsyncGen(["Hello", " world"]))

    with patch("backend.agent.nodes.answer.OllamaClient", return_value=mock_client):
        state = _base_state(
            prompt_mode="GENERAL",
            retrieved_context="",
            model_name="test-model",
        )
        await answer_node(state)

    mock_client.generate_stream.assert_called_once()
    call_kwargs = mock_client.generate_stream.call_args.kwargs
    assert "Retrieved Context" not in call_kwargs.get("system", "")


@pytest.mark.asyncio
async def test_answer_grounded_rag_does_not_fallback_to_general():
    mock_client = MagicMock()
    mock_client.generate_stream = MagicMock(return_value=_AsyncGen(["Based on document..."]))

    with patch("backend.agent.nodes.answer.OllamaClient", return_value=mock_client):
        state = _base_state(
            prompt_mode="GROUNDED_RAG",
            retrieved_context="Industrial safety procedures for valve inspection.",
            model_name="test-model",
        )
        await answer_node(state)

    call_kwargs = mock_client.generate_stream.call_args.kwargs
    system_prompt = call_kwargs.get("system", "")
    assert "RETRIEVED CONTEXT" in system_prompt


@pytest.mark.asyncio
async def test_sources_only_present_when_grounded_rag():
    token_queue = asyncio.Queue()
    state = _base_state(
        prompt_mode="CONSERVATIVE_NO_SOURCE",
        no_match_message_type="audio_no_match",
        sources=[{"source": "should-not-emit.pdf"}],
    )
    result = await answer_node(state, token_queue=token_queue)
    assert result["answer"]
    messages = []
    while not token_queue.empty():
        messages.append(token_queue.get_nowait())
    source_msgs = [m for m in messages if m.get("type") == "sources"]
    assert len(source_msgs) == 0


@pytest.mark.asyncio
async def test_history_context_does_not_leak_across_modes():
    state_groundx = _base_state(
        answer_mode="groundx",
        groundx_results=[
            {
                "content": "grounded info",
                "score": 0.90,
                "source": "gx.pdf",
                "file_id": "gx1",
                "file_name": "gx.pdf",
                "file_type": "pdf",
                "chunk_index": 0,
            }
        ],
    )
    result1 = await context_synthesis_node(state_groundx)
    assert result1["prompt_mode"] == "GROUNDED_RAG"

    state_general = _base_state(
        answer_mode="general",
        groundx_results=[
            {
                "content": "leaked context",
                "score": 0.90,
                "source": "gx.pdf",
                "file_id": "gx1",
                "file_name": "gx.pdf",
                "file_type": "pdf",
                "chunk_index": 0,
            }
        ],
    )
    result2 = await context_synthesis_node(state_general)
    assert result2["prompt_mode"] == "GENERAL"
    assert result2["retrieved_context"] == ""
    assert result2["sources"] == []


# ── Fix 1+2: Post-LLM hedge detection for groundx/audio modes ──


@pytest.mark.asyncio
async def test_groundx_mode_llm_hedge_response_replaced_with_arabic_message():
    hedge_response = (
        "Based on the retrieved text, there is no specific mention of American "
        "protection and allies. If you would like me to answer from general "
        "knowledge, I can do that."
    )
    mock_client = MagicMock()
    mock_client.generate_stream = MagicMock(side_effect=[_AsyncGen(["YES"]), _AsyncGen([hedge_response])])
    queue = asyncio.Queue()
    with patch("backend.agent.nodes.answer.OllamaClient", return_value=mock_client):
        state = _base_state(
            prompt_mode="GROUNDED_RAG",
            retrieved_context="some irrelevant chunk text",
            retrieval_provider="groundx",
            sources=[{"source": "1029-miller0504.pdf", "score": 0.50}],
            model_name="test-model",
        )
        result = await answer_node(state, token_queue=queue)
    assert result["answer"] == "لا توجد معلومات كافية في GroundX للإجابة على هذا السؤال."
    assert result["sources"] == []
    assert result["no_match_message_type"] == "groundx_no_match"
    events = _drain_queue(queue)
    source_index = next(i for i, event in enumerate(events) if event.get("type") == "sources")
    message_index = next(
        i for i, event in enumerate(events)
        if event.get("type") == "token"
        and event["data"]["data"]["token"] == "لا توجد معلومات كافية في GroundX للإجابة على هذا السؤال."
    )
    source_events = [event for event in events if event.get("type") == "sources"]
    assert source_index < message_index
    assert len(source_events) == 1
    assert source_events[0]["data"]["data"]["sources"] == []


@pytest.mark.asyncio
async def test_hedge_detection_catches_isnt_used_specifically():
    hedge_response = "the term computing facilities isn't used specifically in this context"
    mock_client = MagicMock()
    mock_client.generate_stream = MagicMock(side_effect=[_AsyncGen(["YES"]), _AsyncGen([hedge_response])])
    with patch("backend.agent.nodes.answer.OllamaClient", return_value=mock_client):
        state = _base_state(
            prompt_mode="GROUNDED_RAG",
            retrieved_context="audio transcript about a different topic",
            retrieval_provider="qdrant_audio",
            sources=[{"source": "meeting.mp3", "score": 0.70}],
            model_name="test-model",
        )
        result = await answer_node(state)
    assert result["answer"] == "لا توجد معلومات كافية في التسجيلات الصوتية للإجابة على هذا السؤال."
    assert result["sources"] == []
    assert result["no_match_message_type"] == "audio_no_match"


@pytest.mark.asyncio
async def test_hedge_detection_catches_context_does_not():
    hedge_response = "the provided context does not contain information about computing facilities"
    mock_client = MagicMock()
    mock_client.generate_stream = MagicMock(side_effect=[_AsyncGen(["YES"]), _AsyncGen([hedge_response])])
    with patch("backend.agent.nodes.answer.OllamaClient", return_value=mock_client):
        state = _base_state(
            prompt_mode="GROUNDED_RAG",
            retrieved_context="some unrelated PDF text",
            retrieval_provider="groundx",
            sources=[{"source": "manual.pdf", "score": 0.72}],
            model_name="test-model",
        )
        result = await answer_node(state)
    assert result["answer"] == "لا توجد معلومات كافية في GroundX للإجابة على هذا السؤال."
    assert result["sources"] == []
    assert result["no_match_message_type"] == "groundx_no_match"


@pytest.mark.asyncio
async def test_audio_mode_llm_hedge_response_replaced_with_arabic_message():
    hedge_response = (
        "The provided context does not contain information about this topic. "
        "If you would like, I can use general knowledge."
    )
    mock_client = MagicMock()
    mock_client.generate_stream = MagicMock(side_effect=[_AsyncGen(["YES"]), _AsyncGen([hedge_response])])
    with patch("backend.agent.nodes.answer.OllamaClient", return_value=mock_client):
        state = _base_state(
            prompt_mode="GROUNDED_RAG",
            retrieved_context="some audio transcript chunk",
            retrieval_provider="qdrant_audio",
            sources=[{"source": "meeting.mp3", "score": 0.52}],
            model_name="test-model",
        )
        result = await answer_node(state)
    assert result["answer"] == "لا توجد معلومات كافية في التسجيلات الصوتية للإجابة على هذا السؤال."
    assert result["sources"] == []
    assert result["no_match_message_type"] == "audio_no_match"


@pytest.mark.asyncio
async def test_groundx_audio_question_classifier_no_emits_empty_sources_then_arabic_message():
    mock_client = MagicMock()
    mock_client.generate_stream = MagicMock(return_value=_AsyncGen(["NO"]))
    queue = asyncio.Queue()
    with patch("backend.agent.nodes.answer.OllamaClient", return_value=mock_client):
        state = _base_state(
            query="What did the audio meeting say about compressor trips?",
            prompt_mode="GROUNDED_RAG",
            retrieved_context="PDF manual excerpt about valve inspection only.",
            retrieval_provider="groundx",
            sources=[{
                "file_id": "pdf-1",
                "file_name": "manual.pdf",
                "file_type": "pdf",
                "chunk_index": 0,
                "content": "PDF manual excerpt about valve inspection only.",
                "score": 0.82,
            }],
            model_name="test-model",
        )
        result = await answer_node(state, token_queue=queue)

    events = _drain_queue(queue)
    assert result["answer"] == "لا توجد معلومات كافية في GroundX للإجابة على هذا السؤال."
    assert result["sources"] == []
    assert result["no_match_message_type"] == "groundx_no_match"
    assert mock_client.generate_stream.call_count == 1
    assert _event_types(events) == ["thinking", "sources", "token", "done"]
    assert events[1]["data"]["data"]["sources"] == []
    assert events[2]["data"]["data"]["token"] == result["answer"]


@pytest.mark.asyncio
async def test_audio_pdf_question_classifier_rejects_before_missed_hedge_phrase_streams():
    hedge_response = "the retrieved context does not explicitly mention the requested PDF procedure"
    mock_client = MagicMock()
    mock_client.generate_stream = MagicMock(return_value=_AsyncGen([hedge_response]))
    queue = asyncio.Queue()
    with patch("backend.agent.nodes.answer.OllamaClient", return_value=mock_client):
        state = _base_state(
            query="What does the PDF say about the turnaround checklist?",
            prompt_mode="GROUNDED_RAG",
            retrieved_context="Audio transcript about shift handover and pump vibration.",
            retrieval_provider="qdrant_audio",
            sources=[{
                "file_id": "audio-1",
                "file_name": "meeting.mp3",
                "file_type": "audio",
                "chunk_index": 0,
                "content": "Audio transcript about shift handover and pump vibration.",
                "score": 0.74,
            }],
            model_name="test-model",
        )
        result = await answer_node(state, token_queue=queue)

    events = _drain_queue(queue)
    assert result["answer"] == "لا توجد معلومات كافية في التسجيلات الصوتية للإجابة على هذا السؤال."
    assert result["sources"] == []
    assert result["no_match_message_type"] == "audio_no_match"
    assert mock_client.generate_stream.call_count == 1
    assert _event_types(events) == ["thinking", "sources", "token", "done"]
    assert events[1]["data"]["data"]["sources"] == []
    assert events[2]["data"]["data"]["token"] == result["answer"]


@pytest.mark.asyncio
async def test_groundx_pdf_question_classifier_yes_emits_grounded_answer_and_pdf_sources():
    mock_client = MagicMock()
    mock_client.generate_stream = MagicMock(side_effect=[_AsyncGen(["YES"]), _AsyncGen(["Use the valve checklist."])])
    queue = asyncio.Queue()
    with patch("backend.agent.nodes.answer.OllamaClient", return_value=mock_client):
        state = _base_state(
            query="What does the PDF say about valve inspection?",
            prompt_mode="GROUNDED_RAG",
            retrieved_context="PDF manual says to use the valve checklist.",
            retrieval_provider="groundx",
            sources=[{
                "file_id": "pdf-1",
                "file_name": "manual.pdf",
                "file_type": "pdf",
                "chunk_index": 0,
                "content": "PDF manual says to use the valve checklist.",
                "score": 0.91,
            }],
            model_name="test-model",
        )
        result = await answer_node(state, token_queue=queue)

    events = _drain_queue(queue)
    assert result["answer"] == "Use the valve checklist."
    assert len(result["sources"]) == 1
    assert mock_client.generate_stream.call_count == 2
    assert _event_types(events) == ["thinking", "token", "sources", "done"]
    assert events[1]["data"]["data"]["token"] == result["answer"]
    assert events[2]["data"]["data"]["sources"][0]["file_type"] == "pdf"


@pytest.mark.asyncio
async def test_audio_question_classifier_yes_emits_grounded_answer_and_audio_source():
    mock_client = MagicMock()
    mock_client.generate_stream = MagicMock(side_effect=[_AsyncGen(["YES"]), _AsyncGen(["The trip was caused by vibration."])])
    queue = asyncio.Queue()
    with patch("backend.agent.nodes.answer.OllamaClient", return_value=mock_client):
        state = _base_state(
            query="What did the audio say caused the compressor trip?",
            prompt_mode="GROUNDED_RAG",
            retrieved_context="Audio transcript says vibration caused the compressor trip.",
            retrieval_provider="qdrant_audio",
            sources=[{
                "file_id": "audio-1",
                "file_name": "meeting.mp3",
                "file_type": "audio",
                "chunk_index": 0,
                "content": "Audio transcript says vibration caused the compressor trip.",
                "score": 0.88,
            }],
            model_name="test-model",
        )
        result = await answer_node(state, token_queue=queue)

    events = _drain_queue(queue)
    assert result["answer"] == "The trip was caused by vibration."
    assert len(result["sources"]) == 1
    assert mock_client.generate_stream.call_count == 2
    assert _event_types(events) == ["thinking", "token", "sources", "done"]
    assert events[1]["data"]["data"]["token"] == result["answer"]
    assert events[2]["data"]["data"]["sources"][0]["file_type"] == "audio"


@pytest.mark.asyncio
async def test_general_mode_emits_general_answer_without_sources():
    mock_client = MagicMock()
    mock_client.generate_stream = MagicMock(return_value=_AsyncGen(["General answer."]))
    queue = asyncio.Queue()
    with patch("backend.agent.nodes.answer.OllamaClient", return_value=mock_client):
        state = _base_state(
            prompt_mode="GENERAL",
            retrieved_context="",
            sources=[{"file_name": "should-not-emit.pdf", "file_type": "pdf"}],
            model_name="test-model",
        )
        result = await answer_node(state, token_queue=queue)

    events = _drain_queue(queue)
    assert result["answer"] == "General answer."
    assert mock_client.generate_stream.call_count == 1
    assert _event_types(events) == ["thinking", "token", "done"]
    assert [event for event in events if event.get("type") == "sources"] == []


@pytest.mark.asyncio
async def test_classifier_yes_for_semantic_relevance():
    australia_context = (
        "Audio transcript: Australia hosts US military facilities near Darwin, "
        "Tindall, and Perth, and is being integrated into the US kill chain."
    )
    mock_client = MagicMock()
    mock_client.generate_stream = MagicMock(side_effect=[_AsyncGen(["YES"]), _AsyncGen(["Australia hosts US bases."])])
    queue = asyncio.Queue()

    with patch("backend.agent.nodes.answer.OllamaClient", return_value=mock_client):
        state = _base_state(
            query="What does the audio say about American protection and allies?",
            prompt_mode="GROUNDED_RAG",
            retrieved_context=australia_context,
            retrieval_provider="qdrant_audio",
            sources=[{
                "file_id": "audio-1",
                "file_name": "meeting.mp3",
                "file_type": "audio",
                "chunk_index": 0,
                "content": australia_context,
                "score": 0.62,
            }],
            model_name="test-model",
        )
        result = await answer_node(state, token_queue=queue)

    events = _drain_queue(queue)
    assert result["answer"] == "Australia hosts US bases."
    assert result["sources"][0]["file_type"] == "audio"
    assert mock_client.generate_stream.call_count == 2
    assert _event_types(events) == ["thinking", "token", "sources", "done"]


@pytest.mark.asyncio
async def test_classifier_no_override_by_high_score():
    mock_client = MagicMock()
    mock_client.generate_stream = MagicMock(side_effect=[_AsyncGen(["NO"]), _AsyncGen(["High-score grounded answer."])])

    with (
        patch("backend.agent.nodes.answer.OllamaClient", return_value=mock_client),
        patch("backend.agent.nodes.answer.logger.info") as mock_log_info,
    ):
        state = _base_state(
            query="What does the audio say about American protection and allies?",
            prompt_mode="GROUNDED_RAG",
            retrieved_context="Australia hosts US military bases near Darwin and Perth.",
            retrieval_provider="qdrant_audio",
            max_score=0.70,
            sources=[{"file_name": "meeting.mp3", "file_type": "audio", "score": 0.70}],
            model_name="test-model",
        )
        result = await answer_node(state)

    assert result["answer"] == "High-score grounded answer."
    assert mock_client.generate_stream.call_count == 2
    assert any(
        call.args and "CLASSIFIER_OVERRIDE_BY_SCORE max_score=" in call.args[0]
        for call in mock_log_info.call_args_list
    )


@pytest.mark.asyncio
async def test_classifier_no_stays_no_when_score_low():
    mock_client = MagicMock()
    mock_client.generate_stream = MagicMock(return_value=_AsyncGen(["NO"]))

    with patch("backend.agent.nodes.answer.OllamaClient", return_value=mock_client):
        state = _base_state(
            query="What does the audio say about American protection and allies?",
            prompt_mode="GROUNDED_RAG",
            retrieved_context="Unrelated audio transcript about pump vibration.",
            retrieval_provider="qdrant_audio",
            max_score=0.50,
            sources=[{"file_name": "meeting.mp3", "file_type": "audio", "score": 0.50}],
            model_name="test-model",
        )
        result = await answer_node(state)

    assert result["answer"] == "لا توجد معلومات كافية في التسجيلات الصوتية للإجابة على هذا السؤال."
    assert result["sources"] == []
    assert result["no_match_message_type"] == "audio_no_match"
    assert mock_client.generate_stream.call_count == 1


@pytest.mark.asyncio
async def test_classifier_audio_question_about_us_protection_returns_yes():
    australia_context = (
        "The audio says Australia hosts US bases around Darwin, Tindall, "
        "and Perth, with alliance structures that integrate Australia into "
        "the US military kill chain."
    )
    mock_client = MagicMock()
    mock_client.generate_stream = MagicMock(side_effect=[_AsyncGen(["YES"]), _AsyncGen(["It links Australia to US bases."])])

    with patch("backend.agent.nodes.answer.OllamaClient", return_value=mock_client):
        state = _base_state(
            query="What does the audio say about American protection and allies?",
            prompt_mode="GROUNDED_RAG",
            retrieved_context=australia_context,
            retrieval_provider="qdrant_audio",
            sources=[{"file_name": "meeting.mp3", "file_type": "audio", "score": 0.66}],
            model_name="test-model",
        )
        result = await answer_node(state)

    classifier_call = mock_client.generate_stream.call_args_list[0].kwargs
    assert result["answer"] == "It links Australia to US bases."
    assert "Do NOT require exact keyword matches" in classifier_call["system"]
    assert "American protection and allies" in classifier_call["system"]
    assert "American protection and allies" in classifier_call["prompt"]
    assert "Australia hosts US bases" in classifier_call["prompt"]


# ── Fix 3: Higher relevance thresholds for groundx/audio modes ──


@pytest.mark.asyncio
async def test_groundx_mode_higher_relevance_threshold_blocks_low_score_chunks():
    groundx_chunks = [
        {
            "content": "marginally relevant text",
            "score": 0.50,
            "source": "doc.pdf",
            "file_id": "f1",
            "file_name": "doc.pdf",
            "file_type": "pdf",
            "chunk_index": 0,
        },
    ]
    state = _base_state(answer_mode="groundx", groundx_results=groundx_chunks)
    result = await context_synthesis_node(state)
    assert result["prompt_mode"] == "CONSERVATIVE_NO_SOURCE"
    assert result["no_match_message_type"] == "groundx_no_match"
    assert result["sources"] == []


@pytest.mark.asyncio
async def test_audio_mode_threshold_blocks_below_0_48():
    audio_chunks = [
        {
            "content": "marginally relevant audio",
            "score": 0.40,
            "retrieval_score": 0.40,
            "source": "meeting.mp3",
            "file_id": "a1",
            "file_name": "meeting.mp3",
            "file_type": "audio",
            "chunk_index": 0,
        },
    ]
    state = _base_state(answer_mode="audio", qdrant_results=audio_chunks)
    result = await context_synthesis_node(state)
    assert result["prompt_mode"] == "CONSERVATIVE_NO_SOURCE"
    assert result["no_match_message_type"] == "audio_no_match"


@pytest.mark.asyncio
async def test_audio_mode_lower_threshold_allows_relevant_chunks():
    audio_chunks = [
        {
            "content": "audio transcript about American protection and allies",
            "score": 0.50,
            "retrieval_score": 0.50,
            "source": "meeting.mp3",
            "file_id": "a1",
            "file_name": "meeting.mp3",
            "file_type": "audio",
            "chunk_index": 0,
        },
    ]
    state = _base_state(answer_mode="audio", qdrant_results=audio_chunks)
    result = await context_synthesis_node(state)
    assert result["prompt_mode"] == "GROUNDED_RAG"
    assert len(result["sources"]) == 1
    assert result["no_match_message_type"] == ""


@pytest.mark.asyncio
async def test_general_mode_not_affected_by_threshold_changes():
    state = _base_state(answer_mode="general")
    result = await context_synthesis_node(state)
    assert result["prompt_mode"] == "GENERAL"
    assert result["no_match_message_type"] == ""
