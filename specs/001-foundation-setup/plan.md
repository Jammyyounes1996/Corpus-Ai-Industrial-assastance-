# Implementation Plan: Foundation & Setup

**Branch**: `001-foundation-setup` | **Date**: 2026-05-18 | **Spec**: [PLAN.md](../../PLAN.md)
**Input**: Feature specification from PLAN.md - Industrial AI Assistant

## Summary

Phase 1 establishes the foundation for the Industrial AI Assistant project. This phase creates all project scaffolding, configures the development environment, sets up infrastructure services (Qdrant, Ollama), initializes the database with SQLAlchemy models, and gets both FastAPI backend and Streamlit frontend running with health checks.

The primary deliverable is a working development environment where `curl http://localhost:8000/health` returns success and `streamlit run frontend/app.py` displays the basic UI layout (sidebar + tabs).

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI 0.115, Streamlit 1.40, LangGraph 0.2, SQLAlchemy 2.0, Pydantic 2.9
**Storage**: SQLite (via aiosqlite) for relational data, Qdrant (Docker) for vector search, disk storage for uploaded files
**Testing**: pytest with pytest-asyncio
**Target Platform**: Windows 11 (dev), Linux-compatible for future deployment
**Project Type**: web-service (FastAPI backend + Streamlit frontend)
**Performance Goals**: Health check < 100ms, app cold start < 10s
**Constraints**: Local-first (no paid services), requires ~8GB VRAM for Gemma4, GPU acceleration optional
**Scale/Scope**: Single-user desktop application, ~50+ source files planned

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Article | Status | Notes |
|---------|--------|-------|
| Article I - Code Quality | PASS | Template enforces self-documenting code, short functions |
| Article II - Naming | PASS | Will use PEP 8 throughout (snake_case modules, PascalCase classes) |
| Article III - Type Safety | PASS | Pydantic models for API, full type hints required |
| Article IV - Error Handling | PASS | Custom exceptions to be defined per module |
| Article V - Dependencies | PASS | All versions pinned in requirements.txt |
| Article VI - Environment | PASS | pydantic-settings for config, .env.example committed |
| Article VII - Logging | PASS | loguru configured once, structured logging |
| Article VIII - Async | PASS | FastAPI async handlers, httpx.AsyncClient |
| Article IX - Testing | PASS | pytest structure mirrors source tree |
| Article X - Frontend | PASS | Streamlit components as functions, CSS in main.css |
| Article XI - Git | PASS | Conventional commits format |
| Article XII - README | PASS | Will be created in Phase 7 |
| Article XIII - Performance | PASS | Targets documented, lazy loading |
| Article XIV - Security | PASS | Pydantic validation at API boundary |
| Article XV - DoD | PASS | Checklist included |

**Result**: All gates passed. Proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/001-foundation-setup/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api.md           # Backend API contract
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
industrial-ai-assistant/
├── backend/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app entry point
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── chat.py                  # (Phase 3)
│   │       ├── ingest.py                # (Phase 2)
│   │       ├── ocr.py                   # (Phase 5)
│   │       ├── evaluation.py            # (Phase 5)
│   │       ├── projects.py              # (Phase 6)
│   │       ├── files.py                 # (Phase 5)
│   │       └── settings.py              # (Phase 6)
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── state.py                 # (Phase 3)
│   │   │   ├── nodes.py                 # (Phase 3)
│   │   │   ├── graph.py                 # (Phase 3)
│   │   │   ├── tools.py                 # (Phase 3)
│   │   │   └── streaming.py             # (Phase 3)
│   │   │
│   │   ├── ingestion/
│   │   │   ├── __init__.py
│   │   │   ├── pdf_ingestor.py          # (Phase 2)
│   │   │   ├── audio_ingestor.py        # (Phase 2)
│   │   │   ├── image_processor.py       # (Phase 2)
│   │   │   └── chunking.py              # (Phase 2)
│   │   │
│   │   ├── retrieval/
│   │   │   ├── __init__.py
│   │   │   ├── qdrant_client.py         # (Phase 2)
│   │   │   ├── groundx_client.py        # (Phase 2)
│   │   │   └── fusion.py                # (Phase 3)
│   │   │
│   │   ├── evaluation/
│   │   │   ├── __init__.py
│   │   │   └── ragas_eval.py            # (Phase 5)
│   │   │
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── ollama_client.py         # (Phase 2)
│   │       ├── gemini_client.py         # (Phase 6)
│   │       ├── grok_client.py           # (Phase 6)
│   │       └── llm_factory.py           # (Phase 6)
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── database.py                  # Engine + session factory (PHASE 1)
│   │   ├── models.py                    # SQLAlchemy models (PHASE 1)
│   │   ├── crud.py                      # CRUD operations (Phase 2)
│   │   └── migrations/                  # Alembic migrations (PHASE 1)
│   │       └── versions/
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── chat.py                      # (Phase 3)
│   │   ├── ingest.py                    # (Phase 2)
│   │   ├── settings.py                  # (Phase 6)
│   │   └── evaluation.py                # (Phase 5)
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py                  # pydantic-settings (PHASE 1)
│   │
│   └── utils/
│       ├── __init__.py
│       ├── encryption.py                # (Phase 6)
│       ├── logging.py                   # Structured logging (PHASE 1)
│       └── file_helpers.py              # (Phase 2)
│
├── frontend/
│   ├── app.py                           # Streamlit entry point (PHASE 1)
│   │
│   ├── components/
│   │   ├── __init__.py
│   │   ├── sidebar.py                   # (Phase 4)
│   │   ├── status_bar.py                # (Phase 4)
│   │   ├── starburst_icon.py            # (Phase 4)
│   │   ├── thinking_card.py             # (Phase 4)
│   │   ├── message_card.py              # (Phase 4)
│   │   ├── input_bar.py                 # (Phase 4)
│   │   ├── source_chips.py              # (Phase 4)
│   │   └── settings_modal.py            # (Phase 6)
│   │
│   ├── tabs/
│   │   ├── __init__.py
│   │   ├── chat_tab.py                  # (Phase 4)
│   │   ├── documents_tab.py             # (Phase 5)
│   │   ├── ocr_tab.py                   # (Phase 5)
│   │   ├── analysis_tab.py              # (Phase 5)
│   │   └── tools_tab.py                 # (Phase 5)
│   │
│   ├── styles/
│   │   ├── main.css                     # All custom styles (PHASE 1 skeleton, Phase 4 complete)
│   │   └── load_css.py                  # CSS injection helper (PHASE 1)
│   │
│   ├── state/
│   │   ├── __init__.py
│   │   └── session.py                   # Streamlit session state helpers (PHASE 1)
│   │
│   └── utils/
│       ├── __init__.py
│       ├── api_client.py                # All HTTP/SSE calls (PHASE 1 skeleton)
│       └── sse_handler.py               # SSE event parser (PHASE 3)
│
├── data/                                # Created at runtime
│   ├── uploads/                         # PDFs
│   ├── audio/                           # Audio files
│   └── images/                          # OCR images
│
├── tests/
│   ├── backend/
│   │   ├── test_agent.py                # (Phase 7)
│   │   ├── test_ingestion.py            # (Phase 7)
│   │   ├── test_retrieval.py            # (Phase 7)
│   │   └── test_api.py                  # (Phase 7)
│   └── conftest.py                      # (Phase 7)
│
├── scripts/
│   ├── init_db.py                       # Initialize SQLite + Alembic (PHASE 1)
│   ├── setup_qdrant_collection.py      # Create Qdrant collection (PHASE 1)
│   └── verify_environment.py            # Pre-flight checks (PHASE 1)
│
├── docker-compose.yml                   # Qdrant container (PHASE 1)
├── environment.yml                      # Miniconda env definition (PHASE 1)
├── requirements.txt                     # Pip requirements (PHASE 1)
├── .env.example                         # Template env file (PHASE 1)
├── .gitignore                           # (PHASE 1)
├── README.md                            # (Phase 7)
├── PLAN.md                              # This exists (root level)
├── CONSTITUTION.md                      # This exists (root level)
└── specs/                               # This directory (for feature specs)
    └── 001-foundation-setup/
        ├── plan.md                      # This file
        ├── spec.md
        ├── research.md
        ├── data-model.md
        ├── quickstart.md
        ├── contracts/
        └── tasks.md
```

**Structure Decision**: Web application with separate backend (FastAPI) and frontend (Streamlit). Backend follows layered architecture (routes → core → models → database). Frontend is component-based with utility functions for API calls.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

N/A - No violations.

---

## Phase 0: Research

### Unknowns to Resolve

1. **Ollama model compatibility**: Verify Gemma4 works with langchain-ollama 0.2.0 on Windows
2. **Qdrant Docker on Windows**: Confirm Qdrant runs correctly via Docker Desktop
3. **Miniconda + PowerShell**: Validate environment creation workflow on Windows
4. **FastAPI CORS config**: Specific configuration needed for Streamlit on localhost:8501
5. **LangGraph SSE streaming**: Confirm astream_events works reliably with sse-starlette

### Research Tasks

- Task: "Research Ollama Gemma4 compatibility with langchain-ollama 0.2.0 on Windows"
- Task: "Find best practices for FastAPI CORS configuration with Streamlit"
- Task: "Research LangGraph astream_events SSE streaming patterns"
- Task: "Validate Qdrant Docker setup for Windows development environment"
- Task: "Research SQLAlchemy 2.0 async patterns with aiosqlite"

---

## Phase 1: Foundation & Setup

### Deliverables

- [ ] All folder structure created with `__init__.py` files
- [ ] `environment.yml` created
- [ ] `requirements.txt` created with all dependencies pinned
- [ ] `.env.example` created
- [ ] `.gitignore` created
- [ ] `docker-compose.yml` created for Qdrant
- [ ] `backend/config/settings.py` created with pydantic-settings
- [ ] `backend/database/database.py` created (engine + session)
- [ ] `backend/database/models.py` created (all 8 tables: Project, Chat, Message, File, OCRResult, Transcript, AppSettings, EvaluationResult)
- [ ] `backend/utils/logging.py` created (loguru configuration)
- [ ] `scripts/init_db.py` created
- [ ] `scripts/setup_qdrant_collection.py` created
- [ ] `scripts/verify_environment.py` created
- [ ] `backend/main.py` created (minimal FastAPI app with /health endpoint)
- [ ] `frontend/app.py` created (basic layout: sidebar + tabs)
- [ ] `frontend/styles/main.css` created (skeleton with design tokens)
- [ ] `frontend/styles/load_css.py` created
- [ ] `frontend/state/session.py` created
- [ ] `frontend/utils/api_client.py` created (skeleton)
- [ ] SQLite database created with all tables (via Alembic)
- [ ] Qdrant collection `industrial_assistant` created

### Acceptance Criteria

- `curl http://localhost:8000/health` → `{"status": "ok"}`
- `streamlit run frontend/app.py` shows sidebar + tabs (empty content OK)
- `python scripts/verify_environment.py` passes all checks
- Database tables exist and have correct schema
- Qdrant collection has correct vector configuration (768d dense + sparse)

### Database Schema (Phase 1)

Tables to create via Alembic:

```python
class Project(Base):
    id: int (PK, autoincrement)
    name: str (unique, not null)
    created_at: datetime (default now)

class Chat(Base):
    id: str (UUID, PK)
    title: str
    project_id: Optional[int] (FK)
    model_provider: str
    model_name: str
    created_at: datetime
    updated_at: datetime

class Message(Base):
    id: int (PK, autoincrement)
    chat_id: str (FK)
    role: str
    content: str (text)
    thinking_steps: JSON
    retrieved_context: JSON
    attached_files: JSON
    created_at: datetime

class File(Base):
    id: str (UUID, PK)
    original_name: str
    file_type: str
    disk_path: str
    size_bytes: int
    groundx_id: Optional[str]
    qdrant_collection: Optional[str]
    indexing_status: str
    created_at: datetime

class OCRResult(Base):
    id: int (PK, autoincrement)
    file_id: str (FK)
    extracted_text: str (text)
    model_used: str
    created_at: datetime

class Transcript(Base):
    id: int (PK, autoincrement)
    file_id: str (FK)
    transcript_text: str (text)
    duration_seconds: float
    language: str
    created_at: datetime

class AppSettings(Base):
    id: int (PK, always 1 - singleton)
    model_provider: str
    model_name: str
    gemini_api_key_encrypted: Optional[str]
    grok_api_key_encrypted: Optional[str]
    theme: str
    updated_at: datetime

class EvaluationResult(Base):
    id: int (PK, autoincrement)
    chat_id: str (FK)
    message_id: int (FK)
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    created_at: datetime
```

---

## Design Decisions

### Decision 1: Separate Backend and Frontend
**Why**: LangGraph async execution requires SSE streaming, which Streamlit cannot handle cleanly. FastAPI provides reusable backend for future clients.
**Alternatives considered**: Streamlit-only (rejected for streaming limitation), Python multiprocessing (rejected for complexity).

### Decision 2: SQLite with Alembic
**Why**: Single-user desktop app doesn't need PostgreSQL. SQLite is file-based and portable. Alembic provides schema migrations.
**Alternatives considered**: Direct SQL execution (rejected - no versioning), Peewee ORM (rejected - less mature than SQLAlchemy).

### Decision 3: pydantic-settings for Configuration
**Why**: Type-safe config loaded from env vars. Validates at startup. Standard in FastAPI ecosystem.
**Alternatives considered**: python-dotenv only (rejected - no validation), Custom config class (rejected - redundant with Pydantic).

### Decision 4: loguru for Logging
**Why**: Simpler than Python's logging module. Built-in structured logging support. Excellent for async contexts.
**Alternatives considered**: standard logging (rejected - verbose setup), structlog (rejected - loguru is simpler).

---

## Next Steps

After Phase 1 completion:
- Proceed to Phase 2: Ingestion Pipeline
- Run `verify_environment.py` to confirm all services are operational
- Begin implementing PDF ingestor with GroundX integration