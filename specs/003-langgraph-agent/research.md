# Research: LangGraph Agent

**Phase**: 0 | **Date**: 2026-05-22 | **Status**: Complete

## Overview

This document captures research findings for implementing the LangGraph Agent system, including technology choices, architectural decisions, and best practices.

---

## Decision 1: Agent Framework

**Chosen Approach**: LangGraph

### Rationale

LangGraph provides native stateful orchestration for AI agents with built-in streaming capabilities. Key advantages:

- **State Management**: Built-in state passing between nodes eliminates manual context management
- **Streaming Support**: Native `astream_events()` API for real-time token and event streaming
- **LangChain Integration**: Seamless compatibility with existing LangChain tools (Ollama, Qdrant, etc.)
- **Conditional Routing**: Built-in support for conditional edges based on state
- **Observability**: Built-in tracing and debugging tools
- **Maturity**: Active development, good documentation, growing community

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Custom State Machine | Requires building state management, routing, and streaming from scratch |
| LangChain AgentExecutor | Limited streaming support, less control over node execution order |
| Direct LangChain Chain | No multi-step reasoning or conditional branching |

### Implementation Pattern

```python
from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END

class AgentState(TypedDict):
    query: str
    context: str
    answer: str
    sources: list[dict]

def router_node(state: AgentState) -> str:
    """Route query to appropriate retrieval path."""
    if state["query"].startswith("@pdf"):
        return "groundx_retrieve"
    elif state["query"].startswith("@image"):
        return "ocr"
    else:
        return "qdrant_retrieve"

def answer_node(state: AgentState) -> AgentState:
    """Generate final answer using LLM."""
    llm = ChatOllama(model="gemma4:latest")
    response = llm.invoke(f"Context: {state['context']}\nQuestion: {state['query']}")
    state["answer"] = response.content
    return state

# Build graph
graph = StateGraph(AgentState)
graph.add_node("router", router_node)
graph.add_node("answer", answer_node)
graph.add_conditional_edges("router", router_node)
graph.set_entry_point("router")
graph.set_finish_point("answer")

app = graph.compile()
```

---

## Decision 2: State Representation

**Chosen Approach**: TypedDict

### Rationale

TypedDict provides:
- **Type Safety**: Static type checking with mypy
- **Serialization**: Easy JSON serialization for storage
- **Immutability**: Can be made immutable with `typing.Final` annotations
- **LangGraph Compatibility**: Native support for TypedDict state

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Pydantic BaseModel | More complex for simple state passing; serialization overhead |
| dataclass | Less ergonomic for incremental state updates |
| Plain dict | No type safety, IDE support |

### State Schema

```python
from typing import TypedDict, Annotated, Optional
from typing_extensions import TypedDict

class ThinkingStep(TypedDict):
    step: str
    status: str  # pending, in_progress, completed, failed
    node: str
    duration_ms: Optional[int]

class Source(TypedDict):
    file_id: str
    filename: str
    file_type: str
    chunk_index: int
    score: float
    excerpt: str

class AgentState(TypedDict):
    # Input
    query: str
    chat_id: Optional[str]
    attached_files: list[str]

    # Intermediate
    thinking_steps: list[ThinkingStep]
    retrieved_context: str
    sources: list[Source]
    route: Optional[str]

    # Output
    answer: str

    # History (from database)
    history: list[dict]
```

---

## Decision 3: Streaming Protocol

**Chosen Approach**: Server-Sent Events (SSE)

### Rationale

SSE matches the existing Phase 1 API architecture and provides:
- **Unidirectional Streaming**: Server pushes events to client (ideal for token streaming)
- **Auto-Reconnection**: Built-in client reconnection on disconnect
- **Event Types**: Support for multiple event types in single stream
- **Browser Support**: Native `EventSource` API
- **FastAPI Integration**: Native support via `sse-starlette`

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| WebSocket | Bidirectional not needed; more complex setup |
| HTTP Chunked Transfer | No event type support; less robust |
| gRPC Streaming | Overkill for this use case; browser support limited |

### Event Format

```python
# Thinking step event
{
    "event": "thinking_step",
    "data": json.dumps({
        "step": "Analyzing your query...",
        "status": "in_progress",
        "node": "router_node",
        "duration_ms": None
    })
}

# Token event
{
    "event": "token",
    "data": json.dumps({"content": "The main"})
}

# Sources event
{
    "event": "sources",
    "data": json.dumps({
        "sources": [{
            "file_id": "abc-123",
            "filename": "manual.pdf",
            "chunk_index": 3,
            "score": 0.92
        }]
    })
}

# Done event
{
    "event": "done",
    "data": json.dumps({
        "chat_id": "550e8400-e29b-41d4-a716-44665544010",
        "message_id": 42
    })
}
```

---

## Decision 4: Retrieval Fusion Strategy

**Chosen Approach**: Reciprocal Rank Fusion (RRF)

### Rationale

RRF is proven effective for fusing results from multiple retrieval systems:

- **Score Normalization**: Handles different score scales automatically
- **Rank-Based**: Less sensitive to absolute score values
- **Tunable**: Single `k` parameter controls influence
- **Simple**: Easy to implement and understand

### Algorithm

```python
def reciprocal_rank_fusion(results: list[dict], k: int = 60) -> list[dict]:
    """Fuse results from multiple retrieval sources using RRF.

    Args:
        results: List of retrieval results, each with 'results' list
                 containing items with 'id' and 'score'.
        k: RRF parameter (default 60 per Cormack et al. 2009).

    Returns:
        Fused, sorted results with combined RRF scores.
    """
    fused_scores = {}

    for result_set in results:
        for rank, item in enumerate(result_set["results"], start=1):
            item_id = item["id"]
            if item_id not in fused_scores:
                fused_scores[item_id] = {
                    "id": item_id,
                    "score": 0.0,
                    "sources": []
                }
            # RRF formula: 1 / (k + rank)
            fused_scores[item_id]["score"] += 1.0 / (k + rank)
            fused_scores[item_id]["sources"].append(result_set["source"])

    # Sort by RRF score (descending)
    return sorted(fused_scores.values(), key=lambda x: x["score"], reverse=True)
```

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Score Averaging | Requires score normalization across systems |
| Weighted Scoring | More complex to tune weights |
| Concatenation | No ranking, poor result quality |

---

## Decision 5: Error Handling & Retries

**Chosen Approach**: Custom Exceptions + Tenacity

### Rationale

Per constitution Article IV:
- **Custom Exceptions**: Domain-specific error types for clarity
- **Tenacity**: Established retry library with exponential backoff
- **Structured Responses**: User-facing error messages via API

### Exception Hierarchy

```python
class AppError(Exception):
    """Base exception for all application errors."""
    pass

class AgentError(AppError):
    """Errors in agent execution."""
    pass

class NodeExecutionError(AgentError):
    """Error in specific node execution."""
    def __init__(self, node: str, cause: Exception):
        self.node = node
        self.cause = cause
        super().__init__(f"Node '{node}' failed: {cause}")

class RetrievalError(AppError):
    """Errors in retrieval operations."""
    pass

class GroundXError(RetrievalError):
    """GroundX API errors."""
    pass

class QdrantError(RetrievalError):
    """Qdrant errors."""
    pass

class ValidationError(AppError):
    """Input validation errors."""
    pass
```

### Retry Pattern

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=30),
    reraise=True
)
async def call_groundx(query: str) -> dict:
    """Call GroundX API with retry on transient failures."""
    response = await httpx.AsyncClient().post(
        "https://api.groundx.ai/search",
        json={"query": query},
        timeout=15.0
    )
    response.raise_for_status()
    return response.json()
```

---

## Decision 6: Conversation Summarization

**Chosen Approach**: LLM-based Summarization at 50 Turns

### Rationale

- **Context Window Limits**: 50 turns ~ 10K tokens, approaching model limits
- **Semantic Summarization**: LLM captures key points better than truncation
- **2-Sentence Summary**: Balance between brevity and information retention
- **Batch Summarization**: Summarize oldest 20 turns at once

### Algorithm

```python
async def summarize_conversation(chat_id: str, db: aiosqlite.Connection) -> None:
    """Summarize oldest 20 turns when conversation exceeds 50 turns.

    Args:
        chat_id: UUID of the chat session.
        db: Async database connection.
    """
    # Get message count
    count = await db.execute(
        "SELECT COUNT(*) FROM messages WHERE chat_id = ?",
        (chat_id,)
    )
    count = await count.fetchone()

    if count[0] <= 50:
        return

    # Get oldest 20 turns (40 messages: 20 user + 20 assistant)
    cursor = await db.execute(
        """SELECT role, content FROM messages
           WHERE chat_id = ? ORDER BY created_at ASC LIMIT 40""",
        (chat_id,)
    )
    messages = await cursor.fetchall()

    # Build summary prompt
    history = "\n".join(
        f"{role}: {content}" for role, content in messages
    )
    prompt = f"""Summarize the following conversation in 2 sentences.
Focus on key topics and information discussed.

{history}

Summary:"""

    # Generate summary
    llm = ChatOllama(model="gemma4:latest")
    summary = llm.invoke(prompt).content.strip()

    # Replace oldest 20 turns with summary
    await db.execute(
        """UPDATE messages SET content = ?, thinking_steps = NULL,
           retrieved_context = NULL
           WHERE id IN (
               SELECT id FROM messages
               WHERE chat_id = ? ORDER BY created_at ASC LIMIT 40
           )""",
        (f"[Summary]: {summary}", chat_id)
    )
    await db.commit()
```

---

## Decision 7: Source Citation Deduplication

**Chosen Approach**: File-Level Merging with Highest Score

### Rationale

- **User Clarity**: Shows each source file once, not multiple chunks
- **Highest Score**: Represents best match from that file
- **+N More**: Handles cases with many sources (show top 3)

### Algorithm

```python
def deduplicate_sources(sources: list[Source], max_display: int = 3) -> list[Source]:
    """Deduplicate sources by file, keeping highest scoring chunk per file.

    Args:
        sources: List of sources from retrieval.
        max_display: Maximum sources to display fully.

    Returns:
        Deduplicated list, with "+N more" indicator if needed.
    """
    # Group by file
    file_map: dict[str, Source] = {}
    for source in sources:
        file_key = (source["file_id"], source["filename"])
        if file_key not in file_map or source["score"] > file_map[file_key]["score"]:
            file_map[file_key] = source

    # Sort by score and extract
    deduplicated = sorted(file_map.values(), key=lambda x: x["score"], reverse=True)

    # Limit display
    if len(deduplicated) > max_display:
        # Show first N with "+M more"
        return deduplicated[:max_display] + [{
            "file_id": "",
            "filename": f"+{len(deduplicated) - max_display} more sources",
            "file_type": "",
            "chunk_index": 0,
            "score": 0.0,
            "excerpt": ""
        }]

    return deduplicated
```

---

## Best Practices References

### LangGraph
- Official docs: https://langchain-ai.github.io/langgraph/
- State management: https://python.langchain.com/docs/langgraph/how_to/state/
- Streaming: https://python.langchain.com/docs/langgraph/how_to/stream_events/

### RRF Fusion
- Paper: Cormack et al., "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods", SIGIR 2009
- Default `k=60` is empirically proven optimal for most cases

### SSE with FastAPI
- `sse-starlette` documentation: https://github.com/sysid/sse-starlette
- EventSource API: https://developer.mozilla.org/en-US/docs/Web/API/EventSource

---

## Open Questions Resolved

| Question | Resolution |
|----------|------------|
| How to handle LLM timeouts? | 15s timeout per call with 2 retries (60s max total) |
| When to summarize conversations? | At 50 turns, summarize oldest 20 to 2 sentences |
| How to present duplicate citations? | Merge by file, keep highest scoring chunk |
| How to handle stream disconnects? | Best-effort: persist partial message on disconnect |
| Content safety approach? | Use LLM's built-in guardrails, no additional filtering |

---

**Status**: All technical decisions resolved. Ready for Phase 1 design.