"""Agent state definition for LangGraph RAG chat system."""

import operator
from typing import Annotated, Any, Optional, TypedDict


class AgentState(TypedDict):
    # User query text to answer.
    query: str
    # Chat identifier for conversation persistence.
    chat_id: str
    # Optional file IDs attached to this query.
    attached_files: list[str]

    # Selected retrieval routes for the current query.
    routes: list[str]

    # GroundX/PDF retrieval results.
    groundx_results: Annotated[list[dict], operator.add]
    groundx_search_text: str
    # Vector database retrieval results.
    qdrant_results: Annotated[list[dict], operator.add]
    # OCR retrieval results for image attachments.
    ocr_results: list[dict]

    # Synthesized context built from retrieved content (docs/OCR only, no history).
    context: str
    # Retrieved-only context (docs + OCR), used by GROUNDED_RAG prompt path.
    retrieved_context: str
    # Conversation history block (kept separate from retrieved context to avoid contamination).
    history_text: str
    # Selected answer prompt mode: GENERAL | GROUNDED_RAG | CONSERVATIVE_NO_SOURCE | INDUSTRIAL_GENERAL.
    prompt_mode: str
    # Source metadata used for citations.
    sources: list[dict]

    # Final generated assistant answer.
    answer: str
    # Reasoning/thinking step events for UI streaming.
    thinking_steps: list[dict]
    # Query classification category for routing decisions.
    query_category: str
    # Error text if any node fails.
    error: str | None

    # Prior conversation messages used for context.
    history: list[dict[str, Any]]

    # Model provider to use for generation.
    model_provider: str
    # Model name to use for generation.
    model_name: Optional[str]
    # Assistant message ID being streamed.
    message_id: str | None

    # Optional explicit retrieval scope (selected file/project/KB IDs).
    selected_scope: list[str]
    # Trace flags for RAG_TRACE structured logging.
    qdrant_called: bool
    groundx_called: bool
    ocr_called: bool
    # Human-readable reason describing why retrieval was skipped.
    retrieval_skipped_reason: str

    # Explicit answer mode selected by user: "groundx" | "audio" | "general".
    answer_mode: str
    # Provider resolved by router for the current mode.
    retrieval_provider: str
    # Whether global GroundX search is allowed for this mode.
    groundx_global_search_allowed: bool
    # Whether global Qdrant audio search is allowed for this mode.
    qdrant_global_audio_search_allowed: bool
    # Human-readable routing decision for tracing.
    mode_decision: str
    # Type of no-match message to emit when prompt_mode is CONSERVATIVE_NO_SOURCE.
    no_match_message_type: str
    # Explicit task type from frontend: "ocr_image" | "" for task-aware routing.
    task_type: str
    # Whether the router determined that current information requires web search.
    search_required: bool
    # Why web search was requested or skipped.
    search_reason: str | None
    # Whether a real web search provider was called.
    search_used: bool
    # Search provider configuration/runtime failure message.
    search_error: str | None
    # Raw normalized web results.
    web_results: list[dict[str, Any]]
    # Web sources normalized for citations/SSE.
    web_sources: list[dict[str, Any]]
