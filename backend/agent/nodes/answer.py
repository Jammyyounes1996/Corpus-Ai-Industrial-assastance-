from __future__ import annotations

import asyncio
import time

from loguru import logger

from backend.agent.state import AgentState
from backend.agent.streaming import emit_sources, emit_thinking_delta, emit_thinking_step, emit_token
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
Answer directly from your own knowledge, helpfully, in the
user's language.

{anti_phrasing}"""

_INDUSTRIAL_GENERAL_SYSTEM_PROMPT = """You are CORPUS, an industrial AI assistant.

Answer the user's industrial/engineering question from your general
industrial engineering knowledge. Be clear and accurate.
You may add one short closing sentence noting that the user can upload a
specific manual or standard for a grounded answer.

{anti_phrasing}"""

_DETAILED_ANSWER_INSTRUCTIONS = """DETAIL LEVEL RULES:
- If the user asks for a detailed explanation, comprehensive answer, report, or says بالتفصيل / شرح مفصل / تقرير, provide a longer structured response.
- Use short Markdown headings, bullet points, numbered steps when useful, examples, and caveats.
- Do not be unnecessarily brief.
- For Arabic answers, use clear Arabic headings and bullet points with readable Markdown formatting.
"""

_WEB_SEARCH_INSTRUCTIONS = """WEB VERIFICATION RULES:
- WEB SEARCH RESULTS are attached below only when a real web search was executed.
- Use them as supporting evidence for updated/current facts.
- Prefer authoritative and recent sources.
- Cite claims with source titles and links.
- If sources disagree, say so clearly.
- Only say that updated sources were checked when WEB SEARCH RESULTS are actually present.
- For Arabic answers, include the note: تم التحقق من مصادر حديثة
"""

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
    "I could not find matching information in the GroundX documents."
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


def _is_arabic_text(text: str) -> bool:
    return any("\u0600" <= char <= "\u06FF" for char in text)


def _wants_detailed_answer(query: str, answer_mode: str) -> bool:
    normalized = f"{query} {answer_mode}".lower()
    signals = (
        "detailed",
        "detail",
        "comprehensive",
        "deep",
        "report",
        "structured",
        "بالتفصيل",
        "شرح مفصل",
        "تقرير",
        "بشكل مفصل",
    )
    return any(signal in normalized for signal in signals)


def _selected_num_predict(state: AgentState) -> int:
    settings = get_settings()
    target = settings.LONG_ANSWER_NUM_PREDICT if _wants_detailed_answer(state.get("query", ""), state.get("answer_mode", "")) else settings.DEFAULT_NUM_PREDICT
    return max(1, min(target, settings.MAX_NUM_PREDICT))


def _format_web_results(results: list[dict]) -> str:
    lines: list[str] = []
    for index, result in enumerate(results[:5], start=1):
        lines.append(
            f"{index}. {result.get('title', 'Untitled source')}\n"
            f"   URL: {result.get('url', '')}\n"
            f"   Source: {result.get('source', '')}\n"
            f"   Published: {result.get('published_date', '')}\n"
            f"   Snippet: {result.get('snippet', '')}"
        )
    return "\n".join(lines)


_NO_MATCH_MESSAGES = {
    "groundx_no_match": "لا توجد معلومات كافية في GroundX للإجابة على هذا السؤال.",
    "groundx_not_ready": "No GroundX documents are ready for retrieval yet. Please wait until at least one PDF shows Ready for GroundX retrieval.",
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


def _is_ocr_only_request(state: AgentState) -> bool:
    routes = state.get("routes", []) or []
    return (
        state.get("retrieval_provider") == "ocr"
        or state.get("mode_decision") == "image_attachment_ocr"
        or ("ocr" in routes and "qdrant" not in routes and "groundx" not in routes)
    )


def _ocr_answer_text(state: AgentState) -> str:
    return "\n\n".join(
        str(item.get("content", "")).strip()
        for item in state.get("ocr_results", []) or []
        if str(item.get("content", "")).strip()
    )


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


def _trim_groundx_inputs(
    query: str,
    history_text: str,
    retrieved_context: str,
    prompt_mode: str,
    retrieval_provider: str,
) -> tuple[str, str]:
    if retrieval_provider != "groundx" or prompt_mode != "GROUNDED_RAG":
        return history_text, retrieved_context

    settings = get_settings()
    max_context_chars = max(2000, settings.GROUNDX_CONTEXT_MAX_CHARS)
    max_history_chars = min(1200, max_context_chars // 4)
    history_trimmed = history_text[-max_history_chars:] if len(history_text) > max_history_chars else history_text
    context_trimmed = retrieved_context[:max_context_chars] if len(retrieved_context) > max_context_chars else retrieved_context
    return history_trimmed, context_trimmed


async def answer_node(
    state: AgentState,
    token_queue: asyncio.Queue | None = None,
) -> AgentState:
    start_time = time.perf_counter()
    logger.info(f"Executing answer_node for query: {state.get('query', '')[:50]}")

    if token_queue is not None:
        await token_queue.put({
            "type": "workflow",
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
        retrieval_provider = state.get("retrieval_provider", "")
        history_text, retrieved_context = _trim_groundx_inputs(
            state.get("query", ""),
            history_text,
            retrieved_context,
            prompt_mode,
            retrieval_provider,
        )
        state["retrieved_context"] = retrieved_context
        state["context"] = retrieved_context
        state["history_text"] = history_text

        if _is_ocr_only_request(state):
            ocr_text = _ocr_answer_text(state)
            if ocr_text:
                state["answer"] = ocr_text
                logger.info(
                    "answer_node: returning OCR-only answer without LLM "
                    "answer_mode={} retrieval_provider={} mode_decision={}",
                    state.get("answer_mode", ""),
                    state.get("retrieval_provider", ""),
                    state.get("mode_decision", ""),
                )
                if token_queue is not None:
                    await token_queue.put({"type": "answer_delta", "data": emit_token(ocr_text)})
                    await token_queue.put({"type": "done", "data": None})
                return state

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
                    await token_queue.put({"type": "answer_delta", "data": emit_token(message)})
                    await token_queue.put({"type": "done", "data": None})
                return state

        if state.get("search_required") and state.get("search_error"):
            message = state["search_error"]
            if _is_arabic_text(state.get("query", "")):
                message = "هذا الطلب يحتاج بحثا ويب حقيقيا، لكن مزود البحث غير مهيأ حاليا. فعّل WEB_SEARCH_ENABLED واضبط WEB_SEARCH_PROVIDER و WEB_SEARCH_API_KEY ثم أعد المحاولة."
            state["answer"] = message
            if token_queue is not None:
                await token_queue.put({"type": "answer_delta", "data": emit_token(message)})
                await token_queue.put({"type": "done", "data": None})
            return state

        system_prompt = _select_system_prompt(prompt_mode, retrieved_context, state.get("retrieval_provider", ""))
        if _wants_detailed_answer(state.get("query", ""), state.get("answer_mode", "")):
            system_prompt = f"{system_prompt}\n\n{_DETAILED_ANSWER_INSTRUCTIONS}"
        if state.get("search_used") and state.get("web_results"):
            system_prompt = (
                f"{system_prompt}\n\n{_WEB_SEARCH_INSTRUCTIONS}\n"
                f"WEB SEARCH RESULTS:\n{_format_web_results(state.get('web_results', []))}"
            )
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
        selected_num_predict = _selected_num_predict(state)
        tokens: list[str] = []
        ollama_metadata: dict | None = None
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
                num_ctx=settings.OLLAMA_NUM_CTX,
            ):
                if isinstance(token, dict):
                    continue
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
                        await token_queue.put({"type": "answer_delta", "data": emit_token(state["answer"])})
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
            "context_length={} model={} num_predict={} num_ctx={} user_prompt_markers={} system_prompt_markers={} "
            "answer_mode={} retrieval_provider={} mode_decision={} "
            "groundx_global_search_allowed={} qdrant_global_audio_search_allowed={} "
            "no_match_message_type={!r} search_used={} search_required={} search_reason={!r}",
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
            selected_num_predict,
            settings.DEFAULT_NUM_CTX,
            prompt_has_marker,
            system_has_marker,
            state.get("answer_mode", ""),
            state.get("retrieval_provider", ""),
            state.get("mode_decision", ""),
            state.get("groundx_global_search_allowed", False),
            state.get("qdrant_global_audio_search_allowed", False),
            state.get("no_match_message_type", ""),
            bool(state.get("search_used")),
            bool(state.get("search_required")),
            state.get("search_reason"),
        )

        async for chunk in client.chat_stream(
            prompt=prompt,
            model=model_name,
            system=system_prompt,
            temperature=0.1,
            max_tokens=selected_num_predict,
            num_ctx=settings.DEFAULT_NUM_CTX,
        ):
            if chunk.get("done"):
                ollama_metadata = chunk
                continue
            thinking_delta = chunk.get("thinking")
            if isinstance(thinking_delta, str) and thinking_delta:
                if token_queue is not None:
                    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                    await token_queue.put({
                        "type": "thinking_delta",
                        "data": emit_thinking_delta(thinking_delta, elapsed_ms),
                    })
                continue

            answer_delta = chunk.get("content")
            if not isinstance(answer_delta, str) or not answer_delta:
                continue

            tokens.append(answer_delta)
            if token_queue is not None and not should_buffer_for_hedge:
                await token_queue.put({"type": "answer_delta", "data": emit_token(answer_delta)})

        state["answer"] = "".join(tokens)
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        usage = None
        if ollama_metadata:
            prompt_tokens = ollama_metadata.get("prompt_eval_count")
            completion_tokens = ollama_metadata.get("eval_count")
            total_duration = ollama_metadata.get("total_duration")
            done_reason = ollama_metadata.get("done_reason")
            if isinstance(prompt_tokens, int) and isinstance(completion_tokens, int):
                generation_time_ms = duration_ms
                if isinstance(total_duration, int):
                    generation_time_ms = total_duration // 1_000_000
                usage = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "generation_time_ms": generation_time_ms,
                }
                state["usage"] = usage
            logger.info(
                "answer_node ollama_complete model={} num_predict={} done_reason={} eval_count={} prompt_eval_count={} total_duration_ns={}",
                model_name,
                selected_num_predict,
                done_reason,
                completion_tokens,
                prompt_tokens,
                total_duration,
            )

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
                    await token_queue.put({"type": "answer_delta", "data": emit_token(state["answer"])})

        if token_queue is not None and should_buffer_for_hedge and not hedge_detected:
            for token in tokens:
                await token_queue.put({"type": "answer_delta", "data": emit_token(token)})

        if (
            token_queue is not None
            and state.get("sources")
            and (prompt_mode == "GROUNDED_RAG" or state.get("search_used"))
            and not hedge_detected
        ):
            await token_queue.put({"type": "sources", "data": emit_sources(state["sources"])})
        if token_queue is not None:
            await token_queue.put({"type": "done", "data": {"usage": usage} if usage else None})

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
