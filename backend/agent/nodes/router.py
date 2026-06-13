from __future__ import annotations

import time
from loguru import logger

from backend.agent.streaming import emit_thinking_step
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.runnables import RunnableConfig

from backend.config.settings import get_settings
from backend.core.models.ollama_client import OllamaClient
from backend.database import crud
from backend.database.models import Message
from backend.agent.state import AgentState
from backend.agent.query_classifier import QueryCategory, classify_query, classify_search_requirement


settings = get_settings()


async def _has_image_attachment(session: AsyncSession | None, file_ids: list[str]) -> bool:
    if session is None or not file_ids:
        return False
    files = await crud.get_files_by_ids(session, file_ids)
    return any(crud.is_image_file(file) for file in files)


async def summarize_conversation(chat_id: str, session: AsyncSession) -> None:
    """Summarize oldest conversation turns and compress message history."""
    old_messages = await crud.get_chat_messages(session, chat_id=chat_id, limit=40)
    if len(old_messages) < 40:
        return

    history_text = "\n".join(f"{msg.role}: {msg.content}" for msg in old_messages)
    prompt = (
        "Summarize the following conversation in 2 sentences. "
        "Focus on key topics and information discussed.\n\n"
        f"{history_text}\n\n"
        "Summary:"
    )

    llm = OllamaClient()
    summary = (await llm.generate(prompt=prompt, model=settings.DEFAULT_MODEL_NAME)).strip()
    if not summary:
        return

    old_message_ids = [msg.id for msg in old_messages]
    await session.execute(delete(Message).where(Message.id.in_(old_message_ids)))
    await crud.create_message(
        session,
        chat_id=chat_id,
        role="system",
        content=f"[Summary]: {summary}",
    )


async def router_node(
    state: AgentState,
    session: AsyncSession | None = None,
    config: RunnableConfig | None = None,
) -> AgentState:
    """Route the request to retrieval backends based on query classification.

    Architecture rule: retrieval is OFF by default. Routes are only emitted
    when the query has explicit document intent or explicit scope. Industrial
    keywords alone do NOT trigger retrieval.
    """
    start_time = time.perf_counter()
    logger.info(f"Executing router_node for query: {state.get('query', '')[:50]}")
    state.setdefault("thinking_steps", []).append(
        emit_thinking_step(
            "router_node",
            "Analyzing your query...",
            {"node": "router_node", "status": "in_progress"},
        )
    )

    # Defensive reset: never carry retrieved_context / sources between requests.
    state["retrieved_context"] = ""
    state["sources"] = []
    state["qdrant_called"] = False
    state["groundx_called"] = False
    state["ocr_called"] = False
    state["retrieval_skipped_reason"] = ""
    state["search_used"] = False
    state["search_error"] = None
    state["web_results"] = []
    state["web_sources"] = []

    cfg = config or {}
    configurable = cfg.get("configurable", {}) if isinstance(cfg, dict) else {}
    config_session = configurable.get("session") if isinstance(configurable, dict) else None
    db_session = session or config_session

    attached_files = state.get("attached_files") or []
    answer_mode = state.get("answer_mode")
    has_image_attachment = await _has_image_attachment(db_session, attached_files)
    selected_scope = state.get("selected_scope") or []
    has_selected = bool(selected_scope)
    search_required, search_reason = classify_search_requirement(
        state.get("query", ""),
        answer_mode=answer_mode,
        has_attached_files=bool(attached_files),
        has_selected_files=has_selected,
    )
    state["search_required"] = search_required
    state["search_reason"] = search_reason

    if has_image_attachment and answer_mode != "groundx":
        state["routes"] = ["ocr"]
        state["retrieval_provider"] = "ocr"
        state["mode_decision"] = "image_attachment_ocr"
        return state

    if answer_mode is not None:
        if answer_mode == "general":
            state["routes"] = []
            state["retrieval_provider"] = "none"
            state["retrieval_skipped_reason"] = "mode_general"
            state["mode_decision"] = "general_no_retrieval"
            return state

        if answer_mode == "groundx":
            logger.info("Qdrant skipped due to GroundX mode")
            state["routes"] = ["groundx"]
            state["retrieval_provider"] = "groundx"
            state["groundx_global_search_allowed"] = True
            state["mode_decision"] = "groundx_only"
            return state

        if answer_mode == "audio":
            state["routes"] = ["qdrant"]
            state["retrieval_provider"] = "qdrant_audio"
            state["qdrant_global_audio_search_allowed"] = True
            state["mode_decision"] = "audio_qdrant_only"
            return state

        # Unrecognized — fall through to classifier (safety net)

    try:
        if db_session is not None and state.get("chat_id"):
            messages = await crud.get_chat_messages(db_session, chat_id=state["chat_id"], limit=100)
            if len(messages) > settings.CONVERSATION_SUMMARY_LIMIT:
                await summarize_conversation(state["chat_id"], db_session)
                messages = await crud.get_chat_messages(db_session, chat_id=state["chat_id"], limit=100)
            state["history"] = [{"role": msg.role, "content": msg.content} for msg in messages]

        has_attached = bool(attached_files)
        category = classify_query(
            state.get("query", ""),
            has_attached_files=has_attached,
            has_selected_files=has_selected,
        )

        state["query_category"] = category.value
        logger.info(f"Query classified as: {category.value}")

        # Default: no retrieval.
        routes: list[str] = []
        skip_reason = ""

        if category == QueryCategory.GENERAL_CHAT:
            routes = []
            skip_reason = "general_chat_no_retrieval"
        elif category == QueryCategory.INDUSTRIAL_KNOWLEDGE:
            # Industrial concept question — answer from general knowledge.
            routes = []
            skip_reason = "industrial_knowledge_no_retrieval"
        elif category == QueryCategory.CURRENT_ATTACHMENT_QA:
            routes = ["qdrant"]
            if has_attached:
                routes.append("ocr")
        elif category == QueryCategory.FILE_QA:
            # Explicit doc intent + selected scope.
            routes = ["qdrant"]
            if has_selected:
                # GroundX is only useful when there is a real selected scope.
                routes.append("groundx")
        elif category == QueryCategory.RAG_REQUIRED:
            # Explicit doc intent, but no attached files / selected scope:
            # we DO route to qdrant, which will internally refuse to perform a
            # global search and return zero chunks. We deliberately do NOT
            # route to GroundX (it is global by nature and cannot be safely
            # scoped per-request).
            routes = ["qdrant"]
            if has_attached or has_selected:
                routes.append("groundx")
            else:
                skip_reason = "doc_intent_without_scope"
        elif category == QueryCategory.UNKNOWN:
            routes = []
            skip_reason = "unknown_category_no_retrieval"
        else:
            routes = []

        state["routes"] = routes
        if skip_reason:
            state["retrieval_skipped_reason"] = skip_reason

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        state.setdefault("thinking_steps", []).append(
            emit_thinking_step(
                "router_node",
                f"Query classified as {category.value}, routes: {routes}",
                {
                    "node": "router_node",
                    "status": "completed",
                    "duration_ms": duration_ms,
                    "category": category.value,
                    "routes": routes,
                    "attached_files": len(attached_files),
                    "has_selected_scope": has_selected,
                    "search_required": search_required,
                    "search_reason": search_reason,
                },
            )
        )
        return state
    except Exception as exc:
        logger.error(f"router_node failed: {exc}")
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        state.setdefault("thinking_steps", []).append(
            emit_thinking_step(
                "router_node",
                f"Router failed: {exc}",
                {
                    "node": "router_node",
                    "status": "failed",
                    "duration_ms": duration_ms,
                },
            )
        )
        raise
