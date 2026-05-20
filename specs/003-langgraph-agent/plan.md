# Implementation Plan: LangGraph Agent

**Branch**: `004-langgraph-agent` | **Date**: 2026-05-20 | **Spec**: [spec.md](spec.md)

**Note**: This template is filled in by `/speckit-plan` command. See `.specify/templates/plan-template.md` for execution workflow.

## Summary

Build a LangGraph agent system that answers natural language questions over ingested industrial knowledge (PDFs, audio transcripts, images) with streaming thinking steps and source citations. The agent routes queries to appropriate retrieval sources (GroundX, Qdrant, OCR), synthesizes context, and generates answers using Gemma4 or alternate models.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI, LangGraph, langchain-core, langchain-ollama, SSE-starlette, httpx-sse
**Storage**: SQLite (aiosqlite) for chat history and messages, Qdrant (via docker) for vector retrieval, GroundX API for PDF retrieval, disk storage for cached context
**Testing**: pytest, pytest-asyncio
**Target Platform**: Linux/Windows/MacOS (local development)
**Project Type**: Web service backend (FastAPI with SSE streaming)

**Performance Goals**:
- First thinking step within 3 seconds of query submission
- Full answers (including thinking steps) complete within 30 seconds for typical queries
- Streaming token latency averages <200ms between tokens

**Constraints**:
- External service timeout: 15 seconds per call with 2 retries using exponential backoff (total 60s max)
- Conversation memory limit: 50 turns maximum before summarization triggers
- Summarization: 20 oldest turns summarized to 2 sentence overview per turn
- Safety: Use LLM's built-in guardrails; display whatever refusal message model generates

**Scale/Scope**: Single-user mode (no multi-tenant isolation requirements)

## Constitution Check

*Gates determined based on constitution file*

| Gate | Status | Justification |
|-------|--------|---------------|
| Code Quality | Pass | Follows project constitution (CONSTITUTION.md) for clean code, SOLID principles |
| Type Safety | Pass | All public functions use type hints (Python 3.11+) |
| Documentation | Pass | Docstrings on all public APIs using Google style |
| Error Handling | Pass | Custom exceptions per module; structured error responses |
| Dependency Management | Pass | Dependencies pinned to exact versions in requirements.txt |
| Testing | Pass | Minimum 70% coverage for backend/core/, 90%+ for critical paths |
| Frontend Standards | N/A | Backend-only implementation |

All gates passed. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/003-langgraph-agent/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── core/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── state.py              # AgentState TypedDict definition
│   │   ├── nodes.py              # LangGraph node functions
│   │   ├── graph.py              # Graph compilation
│   │   ├── tools.py              # LangChain tool definitions
│   │   └── streaming.py          # SSE event helpers
│   └── retrieval/
│       ├── __init__.py
│       ├── fusion.py             # RRF (Reciprocal Rank Fusion) implementation
│       └── qdrant_client.py      # Already exists from Phase 2; extend if needed
├── api/
│   └── routes/
│       ├── __init__.py
│       └── chat.py               # Chat streaming endpoint
├── schemas/
│   ├── __init__.py
│   └── chat.py                # Pydantic models for chat API
├── database/
│   ├── models.py              # Already exists; add Chat, Message tables
│   └── crud.py                 # Already exists; add chat/message CRUD operations
└── main.py                     # FastAPI app entry; mount chat router
```

**Structure Decision**: Follow existing project structure from Phase 1/2. Agent module in `backend/core/agent/`, API routes in `backend/api/routes/`, schemas in `backend/schemas/`. Database models extend existing `models.py` and `crud.py`.

## Complexity Tracking

> No constitution violations requiring justification.

## Phase 0: Outline & Research

No NEEDS CLARIFICATION remaining. All technical decisions are based on existing PLAN.md architecture and tech stack.

### Key Technical Decisions

| Decision | Chosen Approach | Rationale |
|----------|-----------------|-----------|
| Agent Framework | LangGraph | Provides stateful orchestration, built-in streaming via `astream_events`, and native LangChain integration |
| State Management | TypedDict (AgentState) | Simple, serializable state container for LangGraph |
| Streaming Protocol | Server-Sent Events (SSE) | Matches Phase 1 API architecture; real-time token streaming supported |
| Retrieval Strategy | Hybrid dense + BM25 via Qdrant | Already implemented in Phase 2; reuse existing `qdrant_client.py` |
| Context Synthesis | String concatenation with section headers | Simple approach; sufficient for this scope |
| Failure Handling | Custom exceptions with tenacity retries | Per constitution Article IV; exponential backoff for transient failures |

## Phase 1: Design & Contracts

### Data Model Extensions

**New Entities** (extending Phase 2 schema):

```text
### Chat

Represents a conversation session containing multiple message exchanges.

**Attributes**:
| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| id | str (UUID) | Unique identifier for the session | Auto-generated, primary key |
| title | str | Auto-generated from first message | Max 255 characters |
| project_id | Optional[int] | Reference to Project table | Nullable, FK to projects.id |
| model_provider | str | Model used: "ollama" \| "gemini" \| "grok" | Enum constraint |
| model_name | str | Model name (e.g., "gemma4:latest") | Valid model name |
| created_at | datetime | Session creation timestamp | Auto-generated |
| updated_at | datetime | Last activity timestamp | Auto-updated |

**Relationships**:
- `project_id` → `Project.id` (optional, many-to-one)

### Message

Represents a single message in a conversation.

**Attributes**:
| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| id | int | Unique identifier | Auto-increment, primary key |
| chat_id | str (UUID) | Reference to Chat | Foreign key to Chat.id |
| role | str | "user" or "assistant" | Enum constraint |
| content | str (text) | Message content | No length limit (TEXT) |
| thinking_steps | JSON | List of ThinkingStep objects | Serialized JSON |
| retrieved_context | JSON | List of Source objects | Serialized JSON |
| attached_files | JSON | List of file IDs | Serialized JSON |
| created_at | datetime | Message timestamp | Auto-generated |

**Relationships**:
- `chat_id` → `Chat.id` (many-to-one)

**Foreign Keys to Phase 2 Entities**:
- `attached_files` references `IngestedFile.id` from Phase 2
```

### API Contracts

**POST /api/chat/stream** - Stream agent response with thinking steps

**Request**:
```json
{
  "chat_id": "uuid-or-null-for-new",
  "message": "What is the main function of this machine?",
  "attached_files": ["file-uuid-1", "file-uuid-2"]
}
```

**Response**: SSE stream with event types:

| Event | Data Payload |
|-------|-------------|
| `thinking_step` | `{"step": "Analyzing your query...", "status": "in_progress", "node": "router_node", "duration_ms": null}` |
| `thinking_step` | `{"step": "Analyzing your query...", "status": "completed", "node": "router_node", "duration_ms": 450}` |
| `token` | `{"content": "The main"}` |
| `sources` | `{"sources": [{"file_id": "...", "filename": "manual.pdf", "chunk_index": 3, "score": 0.92}]}` |
| `done` | `{"chat_id": "uuid", "message_id": 42}` |

**Status values**: `pending`, `in_progress`, `completed`, `failed`

**GET /api/chats** - List all chat sessions

**Response**:
```json
{
  "chats": [
    {
      "id": "uuid",
      "title": "Pump maintenance questions",
      "model_provider": "ollama",
      "model_name": "gemma4:latest",
      "created_at": "2026-05-20T12:34:56.789Z",
      "updated_at": "2026-05-20T14:22:11.234Z",
      "message_count": 8
    }
  ]
}
```

**GET /api/chat/{chat_id}** - Get full chat with all messages

**Response**:
```json
{
  "chat": {
    "id": "uuid",
    "title": "...",
    "messages": [
      {
        "id": 1,
        "role": "user",
        "content": "What is the flow rate?",
        "thinking_steps": [],
        "retrieved_context": [],
        "attached_files": [],
        "created_at": "2026-05-20T12:34:56.789Z"
      },
      {
        "id": 2,
        "role": "assistant",
        "content": "...",
        "thinking_steps": [...],
        "retrieved_context": [...],
        "created_at": "2026-05-20T12:35:02.123Z"
      }
    ]
  }
}
```

**DELETE /api/chat/{chat_id}** - Delete a chat session

**Response**: HTTP 204 No Content

### Error Responses

```json
{
  "error": "ValidationError|AgentError|RetrievalError",
  "message": "Human-readable error description",
  "details": {
    "field": "optional_field_name",
    "value": "provided_value"
  }
}
```

**HTTP Status Codes**:
- 200: Success
- 400: Bad request (validation error)
- 404: Chat not found
- 500: Internal server error

### Quickstart Guide

```markdown
# Quickstart: LangGraph Agent

## Prerequisites

1. **Phase 2 complete**: Ingestion pipeline functional with PDFs, audio, images indexed
2. **Backend running**:
   ```bash
   cd industrial-ai-assistant
   conda activate industrial-ai
   uvicorn backend.main:app --reload
   ```
3. **Required services**:
   - Qdrant: `docker-compose up -d qdrant`
   - Ollama: `ollama serve` with `gemma4` pulled
   - GroundX: API key configured in `.env`

## Testing Chat with RAG

### Upload test document (if needed)
```bash
# Upload a PDF (from Phase 2 quickstart)
curl -X POST http://localhost:8000/api/ingest/pdf \
  -H "accept: application/json" \
  -F "file=@pump_manual.pdf"
```

### Ask a question
```bash
# Start a new chat and ask a question
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": null,
    "message": "What is the recommended maintenance interval for bearings?",
    "attached_files": []
  }'
```

### Expected SSE Stream
```
event: thinking_step
data: {"step":"Analyzing your query...","status":"in_progress","node":"router_node"}

event: thinking_step
data: {"step":"Analyzing your query...","status":"completed","node":"router_node","duration_ms":320}

event: thinking_step
data: {"step":"Reading PDF documents...","status":"in_progress","node":"groundx_retrieve_node"}

event: thinking_step
data: {"step":"Reading PDF documents...","status":"completed","node":"groundx_retrieve_node","duration_ms":2450}

event: thinking_step
data: {"step":"Searching memory (RAG)...","status":"in_progress","node":"qdrant_retrieve_node"}

event: thinking_step
data: {"step":"Searching memory (RAG)...","status":"completed","node":"qdrant_retrieve_node","duration_ms":890}

event: thinking_step
data: {"step":"Analyzing information...","status":"in_progress","node":"context_synthesis_node"}

event: thinking_step
data: {"step":"Analyzing information...","status":"completed","node":"context_synthesis_node","duration_ms":210}

event: thinking_step
data: {"step":"Generating answer...","status":"in_progress","node":"answer_node"}

event: token
data: {"content":"The recommended"}

event: token
data: {"content":" maintenance interval"}

event: token
data: {"content":" for bearings"}

event: token
data: {"content":" is every"}

event: token
data: {"content":" 6 months"}

event: sources
data: {"sources":[{"file_id":"...","filename":"pump_manual.pdf","chunk_index":12,"score":0.94}]}

event: token
data: {"content":" based on"}

event: token
data: {"content":" the manufacturer's"}

event: token
data: {"content":" specifications."}

event: done
data: {"chat_id":"550e8400-e29b-41d4-a716-44665544010","message_id":1}
```

## Testing Multi-Turn Context

```bash
# Follow up with a question (use chat_id from previous response)
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "550e8400-e29b-41d4-a716-44665544010",
    "message": "What about the flow rate?",
    "attached_files": []
  }'
```

Expected: System maintains context about pump mentioned earlier.

## Testing with Attached Files

```bash
# Ask a question with attached image
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": null,
    "message": "Tell me about this equipment",
    "attached_files": ["uuid-of-ocr-image"]
  }'
```

Expected: OCR text from image is incorporated into the answer.

## Listing Chats

```bash
# Get all chat sessions
curl http://localhost:8000/api/chats | jq
```

## Deleting a Chat

```bash
# Delete a chat session
curl -X DELETE http://localhost:8000/api/chats/550e8400-e29b-41d4-a716-44665544010
```

### Agent Context Update

The plan reference in `CLAUDE.md` points to this plan file:

```markdown
<!-- SPECKIT START -->
**Current Plan**: specs/003-langgraph-agent/plan.md
**Constitution**: CONSTITUTION.md
<!-- SPECKIT END -->
```

(To be applied after this plan is generated)

## Phase 2: Implementation Plan

> Note: Phase 1 (Design & Contracts) is complete. This section outlines implementation tasks.
>
> Actual task list will be generated by `/speckit-tasks` command.

### Implementation Phases

| Phase | Description | Estimated Tasks |
|-------|-------------|-----------------|
| 1 | Database Schema | 6 tasks (Chat, Message models, indexes, migrations) |
| 2 | Agent Core | 12 tasks (state, nodes, graph, tools, streaming, fusion) |
| 3 | API Routes | 8 tasks (chat streaming endpoint, list chats, get chat, delete chat, validation, CORS) |
| 4 | Multi-Turn Context | 7 tasks (CRUD, message history, conversation summarization, context loading) |
| 5 | Streaming Thinking Steps | 6 tasks (ThinkingStep schema, emission, status transitions, duration tracking) |
| 6 | Source Citations | 6 tasks (Source schema, extraction, ordering, deduplication, "+N more" logic) |
| 7 | CRUD Operations | 7 tasks (chat/message CRUD operations) |
| 8 | Schemas | 7 tasks (Pydantic request/response models) |
| 9 | Integration | 13 tasks (mount router, end-to-end testing, success criteria validation) |
| **Total** | | **72 tasks** |

### Phase 1: Database Schema

1. Create `Chat` SQLAlchemy model in `backend/database/models.py`
2. Create `Message` SQLAlchemy model in `backend/database/models.py`
3. Add indexes for Chat and Message tables
4. Create Alembic migration for new tables

**Acceptance Criteria**:
- `alembic revision --autogenerate -m` generates correct migration
- Migration runs successfully: `alembic upgrade head`
- Tables support JSON columns for thinking_steps, retrieved_context, attached_files

### Phase 2: Agent Core

1. Create `AgentState` TypedDict in `backend/core/agent/state.py`
2. Implement `router_node` in `backend/core/agent/nodes.py`
3. Implement `groundx_retrieve_node` in `backend/core/agent/nodes.py`
4. Implement `qdrant_retrieve_node` in `backend/core/agent/nodes.py`
5. Implement `ocr_node` in `backend/core/agent/nodes.py`
6. Implement `context_synthesis_node` in `backend/core/agent/nodes.py`
7. Implement `answer_node` in `backend/core/agent/nodes.py`
8. Create LangGraph graph in `backend/core/agent/graph.py` with conditional edges
9. Define LangChain tools in `backend/core/agent/tools.py`
10. Create SSE streaming helpers in `backend/core/agent/streaming.py`
11. Implement RRF fusion in `backend/core/retrieval/fusion.py` (if not in Phase 2)

**Acceptance Criteria**:
- Graph compiles without errors: `graph = builder.compile()`
- Graph has 7 nodes with correct conditional routing
- Nodes execute sequentially with proper state flow
- Streaming yields events via `astream_events`

### Phase 3: API Routes

1. Create `backend/api/routes/chat.py` module
2. Implement `POST /api/chat/stream` SSE endpoint with FastAPI
3. Implement `GET /api/chats` endpoint
4. Implement `GET /api/chat/{chat_id}` endpoint
5. Implement `DELETE /api/chat/{chat_id}` endpoint

**Acceptance Criteria**:
- SSE endpoint streams `thinking_step`, `token`, `sources`, and `done` events
- Chat ID validation works (new vs existing)
- Error responses follow JSON format defined in contracts
- CORS configured for Streamlit frontend

### Phase 4: CRUD Operations

1. Implement chat CRUD functions in `backend/database/crud.py`
2. Implement message CRUD functions in `backend/database/crud.py`
3. Add transaction support for creating chat with initial message

**Acceptance Criteria**:
- `create_chat()` generates UUID and persists to database
- `create_message()` stores thinking_steps and retrieved_context as JSON
- `get_chat_messages()` retrieves messages in chronological order
- `delete_chat()` cascades deletes messages with chat

### Phase 5: Schemas

1. Create `backend/schemas/chat.py` module
2. Define `ChatRequest`, `ChatStreamResponse`, `ThinkingStep`, `Source`, `ChatListResponse` Pydantic models
3. Add validation rules (chat_id format, message non-empty)

**Acceptance Criteria**:
- Pydantic validates request bodies automatically
- Type hints match contract definitions
- JSON serialization works for nested structures (thinking_steps, sources)

### Phase 6: Integration

1. Mount chat router in `backend/main.py`
2. Test end-to-end flow with sample PDF, audio, and image
3. Verify multi-turn conversation maintains context

**Acceptance Criteria**:
- POST to `/api/chat/stream` with question returns streamed answer
- Each LangGraph node emits a `thinking_step` event
- Final answer cites correct sources
- Follow-up question maintains conversation context

## Next Steps

1. Review this plan for completeness
2. Run `/speckit-tasks` to generate detailed task list
3. Begin implementation following task order
4. Run validation tests for each phase before proceeding

**Important**: Follow constitution guidelines throughout implementation. All code must be readable, well-documented, and type-annotated.
