# Data Model: LangGraph Agent

**Phase**: 1 | **Date**: 2026-05-22 | **Status**: Complete

## Overview

This document describes the data model for the LangGraph Agent feature, including database entities, relationships, validation rules, and state transitions.

---

## Database Entities

### Chat

Represents a conversation session containing multiple message exchanges.

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | VARCHAR(36) | PRIMARY KEY, UUID | `uuid4()` | Unique identifier for the session |
| `title` | VARCHAR(255) | NOT NULL | Auto-generated | Short description from first message |
| `project_id` | INTEGER | FOREIGN KEY, NULLABLE | `NULL` | Optional reference to Project table |
| `model_provider` | VARCHAR(50) | NOT NULL | `"ollama"` | LLM provider (ollama/gemini/grok) |
| `model_name` | VARCHAR(100) | NOT NULL | `"gemma4:latest"` | Specific model name |
| `created_at` | TIMESTAMP | NOT NULL | `CURRENT_TIMESTAMP` | Session creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL | `CURRENT_TIMESTAMP` | Last activity timestamp |

**Indexes**:
- PRIMARY KEY: `(id)`
- INDEX: `idx_chat_project` ON `(project_id)`
- INDEX: `idx_chat_updated` ON `(updated_at DESC)`

**Validation Rules**:
- `model_provider` must be one of: `ollama`, `gemini`, `grok`
- `title` max length: 255 characters
- `project_id` must reference existing `projects.id` if not NULL

**Lifecycle**:
- State transitions: `active` → `archived` (no deletion, soft delete)
- Title auto-generation: Extract first 50 characters from first user message

---

### Message

Represents a single message in a conversation.

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | — | Unique identifier |
| `chat_id` | VARCHAR(36) | FOREIGN KEY, NOT NULL | — | Reference to Chat |
| `role` | VARCHAR(20) | NOT NULL | — | Message role (user/assistant) |
| `content` | TEXT | NOT NULL | — | Message content (unlimited length) |
| `thinking_steps` | JSON | NULLABLE | `NULL` | Serialized ThinkingStep array |
| `retrieved_context` | JSON | NULLABLE | `NULL` | Serialized Source array |
| `attached_files` | JSON | NULLABLE | `NULL` | Serialized UUID array |
| `created_at` | TIMESTAMP | NOT NULL | `CURRENT_TIMESTAMP` | Message timestamp |

**Indexes**:
- PRIMARY KEY: `(id)`
- INDEX: `idx_message_chat` ON `(chat_id, created_at ASC)`
- INDEX: `idx_message_created` ON `(created_at DESC)`

**Validation Rules**:
- `role` must be one of: `user`, `assistant`
- `content` cannot be empty string
- `chat_id` must reference existing `chat.id`

**Relationships**:
- Belongs to: `Chat` (many-to-one)
- Cascades: Delete when parent `Chat` is deleted

---

## Agent State (Runtime)

### AgentState (TypedDict)

In-memory state object passed between LangGraph nodes.

```python
from typing import TypedDict, Annotated, Optional

class AgentState(TypedDict):
    # Input
    query: str                           # User's question
    chat_id: Optional[str]               # Existing chat UUID or None
    attached_files: list[str]            # File UUIDs to include in context

    # Routing
    route: Optional[str]                 # Next node to execute

    # Retrieval
    pdf_results: list[dict]              # GroundX search results
    vector_results: list[dict]           # Qdrant vector search results
    ocr_results: list[dict]              # OCR extraction results

    # Synthesis
    context: str                         # Combined context from all sources
    sources: list[dict]                  # Deduplicated source citations

    # Output
    answer: str                          # Final generated answer

    # Metadata
    thinking_steps: list[dict]           # Step tracking for UI display
    error: Optional[str]                 # Error message if failed
```

### ThinkingStep (TypedDict)

Represents a single step in the agent's reasoning process.

```python
class ThinkingStep(TypedDict):
    step: str              # Description (e.g., "Analyzing your query...")
    status: str            # pending | in_progress | completed | failed
    node: str              # Node name (e.g., "router_node")
    duration_ms: Optional[int]  # Execution time in milliseconds
```

**State Transitions**:

```
pending → in_progress → completed
pending → in_progress → failed
```

---

### Source (TypedDict)

Represents a document or chunk that contributed to the answer.

```python
class Source(TypedDict):
    file_id: str          # UUID of the file
    filename: str         # Original filename
    file_type: str        # pdf | audio | image
    chunk_index: int      # Index within the file
    score: float          # Similarity score (0-1)
    excerpt: str          # Brief excerpt from the chunk
```

---

## JSON Schemas

### thinking_steps Array

```json
[
  {
    "step": "Analyzing your query...",
    "status": "in_progress",
    "node": "router_node",
    "duration_ms": null
  },
  {
    "step": "Analyzing your query...",
    "status": "completed",
    "node": "router_node",
    "duration_ms": 320
  }
]
```

### retrieved_context Array

```json
[
  {
    "file_id": "abc-123-def",
    "filename": "pump_manual.pdf",
    "file_type": "pdf",
    "chunk_index": 12,
    "score": 0.94,
    "excerpt": "The bearings should be lubricated every 6 months..."
  },
  {
    "file_id": "xyz-456-ghi",
    "filename": "maintenance_note.txt",
    "file_type": "audio",
    "chunk_index": 3,
    "score": 0.87,
    "excerpt": "Technician noted bearing replacement on June 15th..."
  }
]
```

### attached_files Array

```json
["abc-123-def", "xyz-456-ghi"]
```

---

## Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐
│     Project     │1     0..*│      Chat      │
│─────────────────├───────┤─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ name            │       │ title           │
│ ...             │       │ project_id (FK) │
└─────────────────┘       │ model_provider  │
                          │ model_name      │
                          │ created_at      │
                          │ updated_at      │
                          └─────────┬───────┘
                                    │ 1
                                    │
                          0..*      │
                          ┌─────────┴───────┐
                          │     Message     │
                          │─────────────────┤
                          │ id (PK)         │
                          │ chat_id (FK)    │
                          │ role            │
                          │ content         │
                          │ thinking_steps  │
                          │ retrieved_ctx   │
                          │ attached_files  │
                          │ created_at      │
                          └─────────────────┘

                    Foreign Key to Phase 2:
                    Message.attached_files → IngestedFile.id
```

---

## Data Flow

### Query Processing Flow

```
User Query
    │
    ├───► Parse into AgentState
    │         │
    │         ├───► router_node() → determines route
    │         │
    │         ├───► {pdf|vector|ocr}_retrieve_node() → fetches results
    │         │
    │         ├───► context_synthesis_node() → merges results
    │         │
    │         └───► answer_node() → generates answer
    │
    └───► Persist to Database
              │
              ├───► Create Chat (if new)
              ├───► Create Message (user)
              └───► Create Message (assistant) with thinking_steps, sources
```

### Conversation History Loading

```
Database Query:
  SELECT * FROM messages
  WHERE chat_id = ?
  ORDER BY created_at ASC
  LIMIT 100

  → Transform into AgentState.history format
  → Append to context prompt
```

---

## Migration Notes

### From Phase 2 to Phase 3

Phase 2 added `IngestedFile` table. Phase 3 extends schema:

**New Tables**:
- `Chat` - for conversation sessions
- `Message` - for individual messages

**No changes to Phase 2 tables**.

### Backward Compatibility

- Phase 2 ingestion pipeline continues to work unchanged
- Chat/message tables added via Alembic migration
- Foreign key to `IngestedFile` uses existing table

---

## Storage Considerations

### Estimated Growth

| Entity | Estimate per User | 1 Year (1 user) | 1 Year (10 users) |
|--------|-------------------|-----------------|-------------------|
| Chat | ~10 chats/month | 120 | 1,200 |
| Message | ~50 messages/chat | 6,000 | 60,000 |
| JSON overhead | ~2KB/message | 12 MB | 120 MB |

### Performance Optimizations

1. **Index on `(chat_id, created_at)`** for efficient conversation loading
2. **Index on `updated_at DESC`** for chat list ordering
3. **JSON storage**: SQLite TEXT field with manual JSON validation
4. **Pagination**: Use `LIMIT/OFFSET` for large conversations

---

**Status**: Data model complete, validated against spec requirements. Ready for implementation.