from __future__ import annotations

import asyncio
import time

from loguru import logger

from backend.agent.state import AgentState
from backend.agent.streaming import emit_sources, emit_thinking_step, emit_token
from backend.config.settings import get_settings
from backend.core.models.ollama_client import OllamaClient


_ANTI_PHRASING_RULES = (
    "OUTPUT STYLE:\n"
    "- Answer the user's current question directly and naturally.\n"
    "- Speak in your own voice. Do not preface answers by referring to "
    "any text, documents, context, sources, or earlier conversation.\n"
    "- Treat the user's current question independently from earlier topics "
    "unless the user explicitly references them.\n"
)

_GROUNDED_SYSTEM_PROMPT = """You are CORPUS, an industrial AI assistant.

You have been given RETRIEVED CONTEXT that may be relevant to the user's question.

ANSWERING RULES:
1. Use the retrieved context ONLY when it is directly relevant to the user's question.
2. If the retrieved context is irrelevant, incomplete, or off-topic for this specific
   question, IGNORE it. Do not force an answer from unrelated context. In that case,
   say plainly that no relevant grounded information is available for this question
   and answer from general knowledge (or invite the user to share the specific file).
3. When you do use the retrieved context, cite the source you used:
   "According to <file_name>..." or add "Sources: <names>" at the end.
4. If multiple chunks are used, cite all of them.
5. Do not fabricate citations for files that are not in the retrieved context.
6. Never invent content that is not in the retrieved context or general knowledge.

{anti_phrasing}
RETRIEVED CONTEXT:
{retrieved_context}
"""

_GENERAL_SYSTEM_PROMPT = """You are CORPUS, an industrial AI assistant.

The user is asking a general conversational or knowledge question.
Answer directly from your own knowledge, helpfully and concisely, in the
user's language.

{anti_phrasing}"""

_INDUSTRIAL_GENERAL_SYSTEM_PROMPT = """You are CORPUS, an industrial AI assistant.

Answer the user's industrial/engineering question from your general
industrial engineering knowledge. Be clear, accurate, and concise.
You may add one short closing sentence noting that the user can upload a
specific manual or standard for a grounded answer.

{anti_phrasing}"""

_CONSERVATIVE_NO_SOURCE_SYSTEM_PROMPT = """You are CORPUS, an industrial AI assistant.

The user asked about a specific document, file, manual, or attachment, but
no grounded source is available for this question.

Reply in 1-3 sentences that you do not have enough grounded information to
answer accurately, and invite the user to upload the relevant file or ask
a more specific question. Do not invent content.

{anti_phrasing}"""

_STRICT_GROUNDX_SUFFIX = (
    "\n\nSTRICT GROUNDX MODE RULE:\n"
    "If the provided context does not contain information that answers the "
    "question, you MUST respond with ONLY the following message and nothing "
    "else — do not explain, do not offer alternatives, do not use general "
    "knowledge:\n"
    "لا توجد معلومات كافية في GroundX للإجابة على هذا السؤال."
)

_STRICT_AUDIO_SUFFIX = (
    "\n\nSTRICT AUDIO MODE RULE:\n"
    "If the provided context does not contain information that answers the "
    "question, you MUST respond with ONLY the following message and nothing "
    "else — do not explain, do not offer alternatives, do not use general "
    "knowledge:\n"
    "لا توجد معلومات كافية في التسجيلات الصوتية للإجابة على هذا السؤال."
)


def _select_system_prompt(prompt_mode: str, retrieved_context: str, retrieval_provider: str = "") -> str:
    if prompt_mode == "GENERAL":
        return _GENERAL_SYSTEM_PROMPT.format(anti_phrasing=_ANTI_PHRASING_RULES)
    if prompt_mode == "INDUSTRIAL_GENERAL":
        return _INDUSTRIAL_GENERAL_SYSTEM_PROMPT.format(anti_phrasing=_ANTI_PHRASING_RULES)
    if prompt_mode == "CONSERVATIVE_NO_SOURCE":
        return _CONSERVATIVE_NO_SOURCE_SYSTEM_PROMPT.format(anti_phrasing=_ANTI_PHRASING_RULES)
    base = _GROUNDED_SYSTEM_PROMPT.format(
        anti_phrasing=_ANTI_PHRASING_RULES,
        retrieved_context=retrieved_context
        or "(no relevant grounded information was retrieved for this question)",
    )
    if retrieval_provider == "groundx":
        return base + _STRICT_GROUNDX_SUFFIX
    if retrieval_provider == "qdrant_audio":
        return base + _STRICT_AUDIO_SUFFIX
    return base


def _fallback_prompt_mode(category: str, retrieved_context: str) -> str:
    # Defensive fallback if context_synthesis_node did not set prompt_mode.
    # Never auto-promote to GROUNDED_RAG here — context.py is the only place
    # allowed to make that decision (it enforces the relevance gate).
    if category == "GENERAL_CHAT":
        return "GENERAL"
    if category == "INDUSTRIAL_KNOWLEDGE":
        return "INDUSTRIAL_GENERAL"
    if category in ("RAG_REQUIRED", "FILE_QA", "CURRENT_ATTACHMENT_QA"):
        return "CONSERVATIVE_NO_SOURCE"
    if category == "UNKNOWN":
        return "CONSERVATIVE_NO_SOURCE"
    return "GENERAL"


def _build_user_prompt(query: str, history_text: str, prompt_mode: str) -> str:
    if prompt_mode in ("CONSERVATIVE_NO_SOURCE",) or not history_text:
        return f"Question: {query}"
    return (
        "Conversation so far (for continuity only — do not treat as retrieved documents):\n"
        f"{history_text}\n\n"
        f"New question: {query}"
    )


_NO_MATCH_MESSAGES = {
    "groundx_no_match": "لا توجد معلومات كافية في GroundX للإجابة على هذا السؤال.",
    "audio_no_match": "لا توجد معلومات كافية في التسجيلات الصوتية للإجابة على هذا السؤال.",
    "": "لا توجد معلومات كافية للإجابة على هذا السؤال.",
}

_ANSWERABILITY_SYSTEM_PROMPT = (
    "You are a binary relevance classifier. Decide whether the provided "
    "CONTEXT contains information that could help answer the QUESTION, even "
    "partially or indirectly.\n\n"
    "Reply YES if ANY of the following is true:\n"
    "- The context discusses the same topic, entities, or concepts as the "
    "question, even with different wording.\n"
    "- The context provides background, context, or related information that "
    "a thoughtful reader could use to construct an answer.\n"
    "- The context contains specific facts, names, places, or events related "
    "to the question's subject.\n\n"
    "Reply NO only if the context is on a completely unrelated topic - for "
    "example, the question asks about audio content but the context is about "
    "industrial PDF documentation that has no connection to the question's "
    "subject.\n\n"
    "Do NOT require exact keyword matches. A question about \"American "
    "protection and allies\" can be answered by context discussing US military "
    "bases, alliance structures, or specific allied nations like Australia.\n\n"
    "Respond with exactly one word: YES or NO. No other text."
)


def _build_answerability_prompt(query: str, retrieved_context: str) -> str:
    return (
        "Question:\n"
        f"{query}\n\n"
        "Retrieved context:\n"
        f"{retrieved_context}\n\n"
        "Can the question be answered directly and specifically from the retrieved context? "
        "Respond YES or NO only."
    )


def _is_answerability_yes(response: str) -> bool:
    return response.strip().upper().startswith("YES")


def _max_retrieval_score(state: AgentState) -> float | None:
    score = state.get("max_score")
    if isinstance(score, (int, float)):
        return float(score)
    if isinstance(score, str):
        try:
            return float(score)
        except ValueError:
            return None
    return None

_HEDGE_SIGNALS = (
    "no specific mention", "not mentioned", "does not contain",
    "no information", "cannot answer", "not found in",
    "if you would like", "if you'd like", "isn't used",
    "is not used", "isn't mentioned", "is not mentioned",
    "does not appear", "doesn't appear", "no direct mention",
    "not directly", "cannot find", "could not find",
    "the provided context does not", "the context does not",
    "based on the provided context, there is no",
)


async def answer_node(
    state: AgentState,
    token_queue: asyncio.Queue | None = None,
) -> AgentState:
    start_time = time.perf_counter()
    logger.info(f"Executing answer_node for query: {state.get('query', '')[:50]}")

    if token_queue is not None:
        await token_queue.put({
            "type": "thinking",
            "data": emit_thinking_step(
                "answer_node", "Generating final answer...",
                {"node": "answer_node", "status": "in_progress"},
            ),
        })

    try:
        category = state.get("query_category", "UNKNOWN")
        retrieved_context = state.get("retrieved_context", "") or state.get("context", "")
        history_text = state.get("history_text", "")
        prompt_mode = state.get("prompt_mode") or _fallback_prompt_mode(category, retrieved_context)

        # ── No-match fast path: emit Arabic message without calling LLM ──
        if prompt_mode == "CONSERVATIVE_NO_SOURCE":
            msg_type = state.get("no_match_message_type", "")
            if msg_type:
                message = _NO_MATCH_MESSAGES.get(
                    msg_type,
                    _NO_MATCH_MESSAGES[""],
                )
                logger.info(
                    "RAG_FINAL_PROMPT_TRACE prompt_mode=CONSERVATIVE_NO_SOURCE "
                    "no_match_message_type={!r} answer_mode={} retrieval_provider={} "
                    "mode_decision={} groundx_global_search_allowed={} "
                    "qdrant_global_audio_search_allowed={} skipped_llm=True",
                    msg_type,
                    state.get("answer_mode", ""),
                    state.get("retrieval_provider", ""),
                    state.get("mode_decision", ""),
                    state.get("groundx_global_search_allowed", False),
                    state.get("qdrant_global_audio_search_allowed", False),
                )
                state["answer"] = message
                if token_queue is not None:
                    await token_queue.put({"type": "token", "data": emit_token(message)})
                    await token_queue.put({"type": "done", "data": None})
                return state

        system_prompt = _select_system_prompt(prompt_mode, retrieved_context, state.get("retrieval_provider", ""))
        prompt = _build_user_prompt(state["query"], history_text, prompt_mode)

        logger.info(
            "answer_node: category={} prompt_mode={} retrieved_chars={} history_chars={} "
            "sources={} routes={}",
            category,
            prompt_mode,
            len(retrieved_context),
            len(history_text),
            len(state.get("sources", []) or []),
            state.get("routes", []),
        )

        client = OllamaClient()
        settings = get_settings()
        model_name = state.get("model_name") or settings.OLLAMA_MODEL
        tokens: list[str] = []
        retrieval_provider = state.get("retrieval_provider", "")
        should_buffer_for_hedge = (
            retrieval_provider in ("groundx", "qdrant_audio")
            and prompt_mode == "GROUNDED_RAG"
        )

        if should_buffer_for_hedge:
            classifier_tokens: list[str] = []
            async for token in client.generate_stream(
                prompt=_build_answerability_prompt(state["query"], retrieved_context),
                model=model_name,
                system=_ANSWERABILITY_SYSTEM_PROMPT,
                temperature=0.0,
                max_tokens=8,
            ):
                classifier_tokens.append(token)

            answerability_decision = "".join(classifier_tokens)
            if not _is_answerability_yes(answerability_decision):
                max_score = _max_retrieval_score(state)
                if max_score is not None and max_score >= 0.65:
                    logger.info("CLASSIFIER_OVERRIDE_BY_SCORE max_score={:.3f}", max_score)
                else:
                    msg_type = "groundx_no_match" if retrieval_provider == "groundx" else "audio_no_match"
                    logger.info(
                        "answer_node: answerability classifier rejected %s mode response",
                        retrieval_provider,
                    )
                    state["answer"] = _NO_MATCH_MESSAGES[msg_type]
                    state["sources"] = []
                    state["no_match_message_type"] = msg_type
                    if token_queue is not None:
                        await token_queue.put({"type": "sources", "data": emit_sources([])})
                        await token_queue.put({"type": "token", "data": emit_token(state["answer"])})
                        await token_queue.put({"type": "done", "data": None})
                    return state

        # RAG_FINAL_PROMPT_TRACE — diagnostic snapshot of the prompt actually
        # sent to the LLM. Does NOT log secrets or full document content.
        suspicious_markers = (
            "النص", "النصوص", "بناءً على", "بناء على",
            "provided text", "Provided text", "the provided",
            "Sources:", "Source:", "According to", "Based on",
        )
        prompt_has_marker = [m for m in suspicious_markers if m in prompt]
        system_has_marker = [m for m in suspicious_markers if m in system_prompt]
        logger.info(
            "RAG_FINAL_PROMPT_TRACE prompt_mode={} system_prompt_name={} "
            "user_prompt_len={} system_prompt_len={} history_chars={} "
            "context_length={} model={} user_prompt_markers={} system_prompt_markers={} "
            "answer_mode={} retrieval_provider={} mode_decision={} "
            "groundx_global_search_allowed={} qdrant_global_audio_search_allowed={} "
            "no_match_message_type={!r}",
            prompt_mode,
            (
                "GROUNDED" if prompt_mode == "GROUNDED_RAG"
                else "GENERAL" if prompt_mode == "GENERAL"
                else "INDUSTRIAL_GENERAL" if prompt_mode == "INDUSTRIAL_GENERAL"
                else "CONSERVATIVE_NO_SOURCE" if prompt_mode == "CONSERVATIVE_NO_SOURCE"
                else "UNKNOWN"
            ),
            len(prompt),
            len(system_prompt),
            len(history_text),
            len(retrieved_context),
            model_name,
            prompt_has_marker,
            system_has_marker,
            state.get("answer_mode", ""),
            state.get("retrieval_provider", ""),
            state.get("mode_decision", ""),
            state.get("groundx_global_search_allowed", False),
            state.get("qdrant_global_audio_search_allowed", False),
            state.get("no_match_message_type", ""),
        )

        async for token in client.generate_stream(
            prompt=prompt,
            model=model_name,
            system=system_prompt,
            temperature=0.1,
            max_tokens=2048,
        ):
            tokens.append(token)
            if token_queue is not None and not should_buffer_for_hedge:
                await token_queue.put({"type": "token", "data": emit_token(token)})

        state["answer"] = "".join(tokens)

        # ── Post-LLM no-match detection (safety net for groundx/audio modes) ──
        hedge_detected = False
        if should_buffer_for_hedge:
            answer_lower = state["answer"].lower()
            if any(signal in answer_lower for signal in _HEDGE_SIGNALS):
                hedge_detected = True
                msg_type = "groundx_no_match" if retrieval_provider == "groundx" else "audio_no_match"
                logger.info(
                    "answer_node: hedge detected for %s mode, overriding with no-match message",
                    retrieval_provider,
                )
                state["answer"] = _NO_MATCH_MESSAGES[msg_type]
                state["sources"] = []
                state["no_match_message_type"] = msg_type
                if token_queue is not None:
                    await token_queue.put({"type": "sources", "data": emit_sources([])})
                    await token_queue.put({"type": "token", "data": emit_token(state["answer"])})

        if token_queue is not None and should_buffer_for_hedge and not hedge_detected:
            for token in tokens:
                await token_queue.put({"type": "token", "data": emit_token(token)})

        if (
            token_queue is not None
            and state.get("sources")
            and prompt_mode == "GROUNDED_RAG"
            and not hedge_detected
        ):
            await token_queue.put({"type": "sources", "data": emit_sources(state["sources"])})
        if token_queue is not None:
            await token_queue.put({"type": "done", "data": None})

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(
            f"answer_node generated {len(tokens)} tokens in {duration_ms}ms "
            f"(category={category}, prompt_mode={prompt_mode})"
        )
        return state
    except Exception as exc:
        logger.error(f"answer_node failed: {exc}")
        if token_queue is not None:
            await token_queue.put({
                "type": "error",
                "data": {"error": str(exc)},
            })
        raise
