from typing import Any

from datetime import datetime, timezone


def emit_thinking_step(
    step_type: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a workflow step SSE payload.

    Args:
        step_type: Thinking step category.
        content: Human-readable step content.
        metadata: Optional additional step metadata.

    Returns:
        dict[str, Any]: SSE event payload.
    """
    metadata = metadata or {}
    return {
        "event": "workflow_step",
        "data": {
            "type": "workflow_step",
            "node": step_type,
            "status": metadata.get("status", "in_progress"),
            "label": content,
            "duration_ms": metadata.get("duration_ms"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


def emit_thinking_delta(delta: str, elapsed_ms: int | None = None) -> dict[str, Any]:
    """Build a model thinking SSE payload."""
    data: dict[str, Any] = {"delta": delta}
    if elapsed_ms is not None:
        data["elapsed_ms"] = elapsed_ms
    return {"event": "thinking_delta", "data": data}


def emit_token(token: str) -> dict[str, Any]:
    """Build an answer delta SSE payload.

    Args:
        token: Streamed token text.

    Returns:
        dict[str, Any]: SSE event payload.
    """
    return {
        "event": "answer_delta",
        "data": {"delta": token},
    }


def emit_sources(sources: list[dict[str, Any]], max_display: int = 5) -> dict[str, Any]:
    """Build a sources SSE payload.

    Normalizes source dicts to include all fields the frontend SourceReference expects:
    file_id, filename, file_type, chunk_index, score, excerpt.
    """
    normalized: list[dict[str, Any]] = []
    for src in sources[:max_display]:
        normalized.append({
            "file_id": src.get("file_id") or src.get("source", ""),
            "filename": src.get("file_name") or src.get("source", "unknown"),
            "file_type": _normalize_file_type(src.get("file_type") or src.get("type", "text")),
            "chunk_index": int(src.get("chunk_index", 0)),
            "score": float(src.get("score", 0.0)),
            "excerpt": src.get("excerpt") or (src.get("content", "") or "")[:200] or "Retrieved content",
        })
    return {
        "event": "sources",
        "data": {
            "sources": normalized,
            "total_count": len(sources),
            "has_more": len(sources) > max_display,
            "hidden_count": max(0, len(sources) - max_display),
        },
    }


def _normalize_file_type(raw: str) -> str:
    mapping = {
        "groundx": "pdf",
        "qdrant": "text",
        "ocr": "image",
        "pdf": "pdf",
        "audio": "audio",
        "image": "image",
        "text": "text",
    }
    return mapping.get(raw.lower(), "text") if raw else "text"


def emit_done(
    message_id: str,
    chat_id: str,
    usage: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build a completion SSE payload.

    Args:
        message_id: Assistant message identifier.
        chat_id: Chat identifier.
        usage: Optional usage metadata with prompt_tokens, completion_tokens,
               total_tokens, generation_time_ms.

    Returns:
        dict[str, Any]: SSE event payload.
    """
    data: dict[str, Any] = {"message_id": message_id, "chat_id": chat_id}
    if usage is not None:
        data["usage"] = usage
    return {"event": "done", "data": data}


def emit_error(error: str) -> dict[str, Any]:
    """Build an error SSE payload.

    Args:
        error: Error message string.

    Returns:
        dict[str, Any]: SSE event payload.
    """
    return {
        "event": "error",
        "data": {"error": error},
    }


def deduplicate_sources(sources: list[dict], max_display: int = 5) -> list[dict]:
    seen: dict[tuple[str, str], dict] = {}
    for source in sources:
        file_id = str(source.get("file_id") or source.get("source", ""))
        src_type = str(source.get("type", ""))
        key = (file_id, src_type)
        if key not in seen:
            seen[key] = source
        else:
            existing = seen[key]
            if float(source.get("score", 0)) > float(existing.get("score", 0)):
                seen[key] = source

    deduped = list(seen.values())
    return deduped[:max_display]
