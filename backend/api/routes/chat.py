from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import json
from loguru import logger
from typing import Any, AsyncGenerator, TypeAlias

from backend.agent import AgentError, RetrievalError
from backend.agent.graph import build_graph
from backend.agent.state import AgentState
from backend.agent.streaming import emit_done, emit_error, emit_sources, emit_thinking_step, emit_token
from backend.config.settings import get_settings
from backend.database import crud
from backend.database.database import get_session
from backend.schemas.chat import ChatCreate, ChatResponse, StreamRequest

router = APIRouter(prefix="/api", tags=["chat"])
settings = get_settings()

CHAT_CORS_ORIGINS = ["http://localhost:8501"]
CHAT_CORS_METHODS = ["GET", "POST", "DELETE", "OPTIONS"]
CHAT_CORS_HEADERS = ["Content-Type", "Authorization"]

ChatListResponse: TypeAlias = list[dict[str, Any]]
ChatDetailResponse: TypeAlias = dict[str, Any]


def is_valid_uuid(chat_id: str) -> bool:
    try:
        uuid.UUID(chat_id)
        return True
    except Exception:
        return False


def error_response(
    error_type: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "error": error_type,
        "message": message,
        "details": details or {},
    }


def _chat_to_dict(chat: Any) -> dict[str, Any]:
    return {
        "id": chat.id,
        "title": chat.title,
        "model_provider": chat.model_provider,
        "model_name": chat.model_name,
        "created_at": chat.created_at.isoformat() if chat.created_at else None,
        "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
    }


def configure_chat_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CHAT_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=CHAT_CORS_METHODS,
        allow_headers=CHAT_CORS_HEADERS,
    )


@router.get("/chats")
async def list_chats(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> ChatListResponse:
    """List all chats.

    Args:
        session: Database session dependency.

    Returns:
        list[dict]: Chat list response.
    """
    chats = await crud.get_chats(session, limit=limit, offset=offset)
    return [_chat_to_dict(chat) for chat in chats]


@router.post("/chats", status_code=status.HTTP_201_CREATED)
async def create_chat(
    payload: ChatCreate,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Create a new chat.

    Args:
        payload: Chat creation request payload.
        session: Database session dependency.

    Returns:
        dict: Created chat response.
    """
    title = (payload.title or "New Chat").strip() or "New Chat"
    model_provider = (payload.model_provider or "ollama").strip() or "ollama"
    model_name = payload.model_name or settings.DEFAULT_MODEL_NAME
    chat = await crud.create_chat(
        session,
        title=title,
        model_provider=model_provider,
        model_name=model_name,
    )
    return _chat_to_dict(chat)


@router.get("/chat/{chat_id}")
async def get_chat(
    chat_id: str,
    session: AsyncSession = Depends(get_session),
) -> ChatDetailResponse:
    """Get a chat and its messages by ID.

    Args:
        chat_id: Chat identifier path parameter.
        session: Database session dependency.

    Returns:
        dict: Chat detail response.
    """
    if not is_valid_uuid(chat_id):
        raise HTTPException(
            status_code=400,
            detail=error_response("validation_error", f"Invalid chat_id format: {chat_id}"),
        )

    chat = await crud.get_chat(session, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail=error_response("not_found", "Chat not found"))

    data = _chat_to_dict(chat)
    data["messages"] = [
        {
            "id": msg.id,
            "chat_id": msg.chat_id,
            "role": msg.role,
            "content": msg.content,
            "thinking_steps": msg.thinking_steps,
            "retrieved_context": msg.retrieved_context,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        }
        for msg in chat.messages
    ]
    return data


@router.delete("/chat/{chat_id}")
async def delete_chat(
    chat_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    """Delete a chat by ID.

    Args:
        chat_id: Chat identifier path parameter.
        session: Database session dependency.

    Returns:
        dict: Deletion status response.
    """
    if not is_valid_uuid(chat_id):
        raise HTTPException(
            status_code=400,
            detail=error_response("validation_error", f"Invalid chat_id format: {chat_id}"),
        )

    deleted = await crud.delete_chat(session, chat_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=error_response("not_found", "Chat not found"))
    return {"deleted": True}


@router.post("/chat/{chat_id}/stream")
async def stream_chat(
    chat_id: str,
    payload: StreamRequest,
    session: AsyncSession = Depends(get_session),
) -> EventSourceResponse:
    """Stream chat response events for a chat."""
    if not is_valid_uuid(chat_id):
        raise HTTPException(status_code=400, detail="Invalid chat_id format")

    logger.info(
        "Incoming chat stream request, chat_id={} query_len={} attached_files={}",
        chat_id,
        len(payload.query or ""),
        len(payload.attached_files or []),
    )
    chat = await crud.get_chat(session, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail=error_response("not_found", "Chat not found"))

    attached_files = payload.attached_files or []
    if attached_files:
        found = await crud.get_files_by_ids(session, attached_files)
        found_ids = {f.id for f in found}
        missing = [fid for fid in attached_files if fid not in found_ids]
        if missing:
            raise HTTPException(status_code=404, detail=f"Files not found: {missing}")

    await crud.create_message(
        session,
        chat_id=chat_id,
        role="user",
        content=payload.query,
        attached_files=payload.attached_files or [],
    )

    assistant_message = await crud.create_message(
        session,
        chat_id=chat_id,
        role="assistant",
        content="",
    )

    state: AgentState = {
        "query": payload.query,
        "chat_id": chat_id,
        "attached_files": payload.attached_files or [],
        "routes": [],
        "groundx_results": [],
        "groundx_search_text": "",
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
        "model_provider": chat.model_provider,
        "model_name": chat.model_name,
        "message_id": assistant_message.id,
        "selected_scope": [],
        "qdrant_called": False,
        "groundx_called": False,
        "ocr_called": False,
        "retrieval_skipped_reason": "",
        "answer_mode": payload.answer_mode,
        "retrieval_provider": "",
        "groundx_global_search_allowed": False,
        "qdrant_global_audio_search_allowed": False,
        "mode_decision": "",
        "no_match_message_type": "",
        "task_type": payload.task_type or "",
        "search_required": False,
        "search_reason": None,
        "search_used": False,
        "search_error": None,
        "web_results": [],
        "web_sources": [],
    }

    import asyncio
    token_queue: asyncio.Queue = asyncio.Queue()
    graph = build_graph(session, token_queue=token_queue)

    def _sse(event_name: str, data: dict[str, Any]) -> dict[str, str]:
        return {"event": event_name, "data": json.dumps(data)}

    async def event_stream() -> AsyncGenerator[dict[str, str], None]:
        collected_workflow_steps: list[dict[str, Any]] = []
        collected_thinking_text_parts: list[str] = []
        collected_sources: list[dict[str, Any]] = []
        answer_text_parts: list[str] = []
        usage_metadata: dict[str, int] | None = None
        done_sent = False

        async def _run_graph() -> dict[str, Any]:
            return await graph.ainvoke(
                state,
                config={"configurable": {"session": session}},
            )

        graph_task = asyncio.create_task(_run_graph())

        try:
            while True:
                try:
                    event = await asyncio.wait_for(token_queue.get(), timeout=120.0)
                except asyncio.TimeoutError:
                    logger.warning("Token queue timeout — ending stream")
                    break

                event_type = event.get("type", "")

                if event_type == "workflow":
                    payload_data = event["data"]
                    collected_workflow_steps.append(payload_data["data"])
                    yield _sse(payload_data["event"], payload_data["data"])

                elif event_type == "thinking_delta":
                    payload_data = event["data"]
                    thinking_text = payload_data.get("data", {}).get("delta", "")
                    collected_thinking_text_parts.append(thinking_text)
                    yield _sse(payload_data["event"], payload_data["data"])

                elif event_type == "answer_delta":
                    payload_data = event["data"]
                    token_text = payload_data.get("data", {}).get("delta", "")
                    answer_text_parts.append(token_text)
                    yield _sse(payload_data["event"], payload_data["data"])

                elif event_type == "sources":
                    payload_data = event["data"]
                    collected_sources.extend(
                        payload_data.get("data", {}).get("sources", [])
                    )
                    yield _sse(payload_data["event"], payload_data["data"])

                elif event_type == "done":
                    done_data = event.get("data")
                    if isinstance(done_data, dict) and isinstance(done_data.get("usage"), dict):
                        usage_metadata = done_data["usage"]
                    break

                elif event_type == "error":
                    error_msg = event.get("data", {}).get("error", "Unknown error")
                    error_payload = emit_error(error_msg)
                    yield _sse(error_payload["event"], error_payload["data"])
                    break

            if not graph_task.done():
                try:
                    await asyncio.wait_for(graph_task, timeout=10.0)
                except asyncio.TimeoutError:
                    graph_task.cancel()

            answer_text = "".join(answer_text_parts)

            if graph_task.done() and not graph_task.cancelled():
                exc = graph_task.exception()
                if exc:
                    logger.error(f"Graph execution failed: {exc}")
                    error_payload = emit_error("An internal error occurred. Please try again.")
                    yield _sse(error_payload["event"], error_payload["data"])
                else:
                    final_state = graph_task.result()
                    if isinstance(final_state, dict):
                        if usage_metadata is None and isinstance(final_state.get("usage"), dict):
                            usage_metadata = final_state["usage"]
                        if not answer_text:
                            answer_text = final_state.get("answer", "")
                            if answer_text:
                                payload_data = emit_token(answer_text)
                                yield _sse(payload_data["event"], payload_data["data"])
                        logger.info(
                            "RAG_TRACE chat_id={} message_id={} query={!r} category={} "
                            "routes={} qdrant_called={} groundx_called={} ocr_called={} "
                            "attached_files={} selected_scope={} context_length={} "
                            "relevant_chunks={} source_files={} prompt_mode={} "
                            "history_chars={} retrieval_skipped_reason={!r} "
                            "answer_mode={} retrieval_provider={} "
                            "search_required={} search_reason={!r} search_used={} "
                            "groundx_global_search_allowed={} "
                            "qdrant_global_audio_search_allowed={} "
                            "mode_decision={!r} "
                            "answer_chars={}",
                            chat_id,
                            assistant_message.id,
                            (payload.query or "")[:120],
                            final_state.get("query_category", ""),
                            final_state.get("routes", []),
                            bool(final_state.get("qdrant_called")),
                            bool(final_state.get("groundx_called")),
                            bool(final_state.get("ocr_called"))
                            or bool(final_state.get("ocr_results")),
                            list(final_state.get("attached_files") or []),
                            list(final_state.get("selected_scope") or []),
                            len(final_state.get("retrieved_context", "") or ""),
                            len(final_state.get("sources", []) or [])
                            if final_state.get("prompt_mode") == "GROUNDED_RAG"
                            else 0,
                            [
                                (s.get("file_name") or s.get("source") or "")
                                for s in (final_state.get("sources", []) or [])
                            ],
                            final_state.get("prompt_mode", ""),
                            len(final_state.get("history_text", "") or ""),
                            final_state.get("retrieval_skipped_reason", "") or "",
                            final_state.get("answer_mode", ""),
                            final_state.get("retrieval_provider", ""),
                            bool(final_state.get("search_required")),
                            final_state.get("search_reason"),
                            bool(final_state.get("search_used")),
                            bool(final_state.get("groundx_global_search_allowed")),
                            bool(final_state.get("qdrant_global_audio_search_allowed")),
                            final_state.get("mode_decision", "") or "",
                            len(answer_text or ""),
                        )

            await crud.update_message_content(
                session,
                assistant_message.id,
                content=answer_text,
                thinking_steps=json.dumps(collected_workflow_steps),
                retrieved_context=json.dumps(collected_sources),
            )
            done_payload = emit_done(assistant_message.id, chat_id, usage_metadata)
            yield _sse(done_payload["event"], done_payload["data"])
            done_sent = True

        except Exception:
            logger.exception("Stream error occurred")
            if not graph_task.done():
                graph_task.cancel()
            answer_text = "".join(answer_text_parts)
            await crud.update_message_content(
                session,
                assistant_message.id,
                content=answer_text,
                thinking_steps=json.dumps(collected_workflow_steps),
                retrieved_context=json.dumps(collected_sources),
            )
            error_payload = emit_error("An internal error occurred. Please try again.")
            yield _sse(error_payload["event"], error_payload["data"])
        finally:
            if not done_sent:
                done_payload = emit_done(assistant_message.id, chat_id, usage_metadata)
                yield _sse(done_payload["event"], done_payload["data"])

    return EventSourceResponse(event_stream())
