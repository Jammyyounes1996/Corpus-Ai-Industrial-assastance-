# Implementation Plan: Ingestion Pipeline

**Branch**: `003-ingestion-pipeline` | **Date**: 2026-05-19 | **Spec**: [spec.md](./spec.md)

**Note**: This template is filled in by `/speckit-plan` command. See `.specify/templates/plan-template.md` for execution workflow.

## Summary

Implement multi-modal file ingestion pipeline enabling industrial engineers to upload, process, and search across PDF documents, audio recordings, and images. The system will integrate with GroundX for PDF processing, Faster-Whisper for audio transcription, and Gemma4 vision for image OCR, with all content indexed in Qdrant vector store for hybrid search retrieval.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI, Faster-Whisper, GroundX SDK, Qdrant Client, LangChain-Ollama, SQLAlchemy 2.0, Pydantic
**Storage**: SQLite (metadata), Qdrant (vectors), Disk (file storage in data/), GroundX (PDF indexing)
**Testing**: pytest, pytest-asyncio, pytest-cov
**Target Platform**: Linux/Windows/macOS (cross-platform development), Docker (Qdrant deployment)
**Project Type**: web-service (backend API with async ingestion + frontend UI)
**Performance Goals**: PDF ingestion < 5 minutes (100MB), Audio transcription < 3 minutes GPU / < 30 min CPU, OCR < 10 seconds, Hybrid search < 500ms
**Constraints**: File size limits (PDF: 100MB, Audio: 100MB, Image: 25MB), CPU fallback for audio when GPU unavailable, External service dependency on GroundX, Concurrent uploads < 10 simultaneous
**Scale/Scope**: Single-user local-first deployment, Knowledge base limited by disk storage, Vector collection: industrial_assistant with 768-dim dense + BM25 sparse

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| 1.1 Clean Code Principles | PASS | Implementation will follow function brevity, no magic numbers, single responsibility |
| 1.2 SOLID & DRY | PASS | Module separation for PDF, audio, image ingestion; shared CRUD utilities |
| 1.3 File Organization | PASS | One file per ingestion type, max 400 lines per file |
| 2.1 Python Naming | PASS | PEP 8 compliance enforced via ruff |
| 3.1 Type Hints | PASS | All public functions annotated, Pydantic at API boundaries |
| 4.1 Exception Strategy | PASS | Custom exceptions: IngestionError, PDFProcessingError, TranscriptionError, OCRError |
| 5.1 Library Selection | PASS | All libraries from existing plan (Phase 1), no new dependencies |
| 6.1 Environment Management | PASS | Use existing pydantic-settings, no hardcoded values |
| 6.2 Configuration | PASS | Settings from backend/config/settings.py, validate at startup |
| 7.1 Logging Standards | PASS | Use existing loguru configuration from Phase 1 |
| 8.1 Async Discipline | PASS | FastAPI async handlers, httpx.AsyncClient, aiosqlite |
| 9.1 Test Coverage | PASS | Minimum 70% coverage, 90% for critical paths |
| 10.1 Component Discipline | PASS | Streamlit components separate from business logic |
| 11.1 Commits | PASS | Conventional commits, one logical change per commit |
| 13.1 General Principles | PASS | Measure before optimize, lazy load models |
| 14.1 Input Validation | PASS | Pydantic validation at API boundary, file size/MIME enforcement |
| 14.2 SQL Safety | PASS | SQLAlchemy ORM only, no string concatenation |

## Project Structure

### Documentation (this feature)

```text
specs/002-ingestion-pipeline/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── api.md           # Ingestion API contracts
│   └── events.md        # SSE event contracts
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
# Existing structure from Phase 1, additions for Phase 2 highlighted:

backend/
├── core/
│   ├── ingestion/              # NEW
│   │   ├── __init__.py
│   │   ├── pdf_ingestor.py        # PDF → GroundX → index
│   │   ├── audio_ingestor.py       # Audio → Whisper → chunks → Qdrant
│   │   ├── image_processor.py       # Image → Gemma4 vision → OCR
│   │   └── chunking.py            # Semantic chunking for transcripts
│   │
│   ├── retrieval/               # NEW
│   │   ├── __init__.py
│   │   ├── qdrant_client.py         # Hybrid search wrapper
│   │   ├── groundx_client.py        # GroundX PDF processor
│   │   └── fusion.py               # RRF implementation
│   │
│   └── models/                  # EXISTING (extend)
│       ├── __init__.py
│       └── ollama_client.py         # Existing, add embedding calls
│
├── api/
│   └── routes/
│       ├── __init__.py
│       ├── ingest.py               # NEW: /api/ingest/{pdf,audio,image}
│       ├── files.py                # NEW: /api/files (list, delete, download)
│       └── chat.py                # EXISTING (will be extended in Phase 3)
│
├── database/
│   ├── crud.py                 # NEW: CRUD for File, Transcript, OCRResult
│   └── models.py                # EXISTING (File, Transcript, OCRResult tables already defined)
│
└── schemas/
    └── ingest.py               # NEW: Ingestion request/response models

frontend/
├── components/                # NEW components
│   ├── file_uploader.py         # File upload with progress
│   ├── file_card.py             # Knowledge base file display
│   ├── status_badge.py          # Indexing status indicator
│   └── delete_confirmation.py   # File deletion modal
│
├── tabs/
│   └── documents_tab.py         # NEW: Knowledge base grid view
│
└── utils/
    └── file_helpers.py          # NEW: File size validation, type checking

tests/
├── backend/
│   ├── test_ingestion.py        # NEW: Test all ingestion flows
│   └── test_retrieval.py       # NEW: Test hybrid search
│
└── fixtures/
    └── sample_files/           # NEW: Test files (PDF, audio, image)
```

**Structure Decision**: Web application structure (backend + frontend) chosen because this project is a full-stack application with separate API and UI. Backend handles all file processing and indexing asynchronously, while Streamlit frontend provides upload interface and file management UI. This separation allows backend to be reusable for future clients (CLI, mobile).

## Complexity Tracking

No constitution violations. Implementation follows all principles. No complexity tracking needed.

---

## Phase 0: Research & Decisions

> **Output**: `research.md` with all NEEDS CLARIFICATION resolved

### Research Tasks

1. **GroundX API integration patterns** - Research best practices for:
   - PDF upload and indexing workflow
   - Polling mechanism for indexing status
   - Error handling for service timeouts
   - Rate limiting considerations

2. **Faster-Whisper GPU/CPU detection** - Research:
   - CUDA detection patterns for Python
   - Appropriate compute types (float16 vs int8)
   - Fallback behavior and user notification

3. **Semantic chunking strategies** - Research:
   - Token count-based vs. sentence-based chunking
   - Overlap strategies for context preservation
   - Best practices for ~500 token chunks

4. **Hybrid search implementation** - Research:
   - Qdrant hybrid (dense + sparse) query API
   - Reciprocal Rank Fusion (RRF) algorithm
   - Parameter tuning (k value, RRF constant)

5. **MIME type validation** - Research:
   - python-magic library usage
   - Content-Type header validation
   - Cross-platform file type detection

---

## Phase 1: Design & Contracts

> **Prerequisites**: `research.md` complete

### 1. Data Model

Create `data-model.md` documenting:
- **IngestedFile** entity with all attributes and state transitions
- **Transcript** entity with language detection and duration
- **OCRResult** entity with extracted text and model used
- **Chunk** entity with vector metadata
- **Relationships** between all entities
- **Validation rules** from spec requirements

### 2. API Contracts

Create `contracts/api.md` documenting:
- `POST /api/ingest/pdf` - request/response, error codes
- `POST /api/ingest/audio` - request/response, error codes
- `POST /api/ingest/image` - request/response, error codes
- `GET /api/files` - query parameters, response schema
- `DELETE /api/files/{id}` - error codes

Create `contracts/events.md` documenting SSE events (future Phase 3):
- `processing_progress` - for long-running ingestion
- `indexing_complete` - when file is searchable

### 3. Quickstart Guide

Create `quickstart.md` with:
- Environment setup for ingestion dependencies
- Testing each ingestion type independently
- Sample curl commands for each endpoint
- Verification queries for ingested content

### 4. Agent Context Update

Update `CLAUDE.md` to reference this plan:
```markdown
## Current Plan

Phase 2: Ingestion Pipeline → `specs/002-ingestion-pipeline/plan.md`
```

---

## Phase 2: Implementation

> **Prerequisites**: Phase 1 artifacts complete
> **Output**: `tasks.md` via `/speckit-tasks` command

**Implementation will be organized by user story:**

1. **User Story 1: PDF Ingestion (P1)**
   - Setup GroundX client
   - Implement PDF ingestor
   - Create /api/ingest/pdf endpoint
   - Add CRUD for PDF file records

2. **User Story 2: Audio Transcription (P1)**
   - Setup Faster-Whisper with GPU detection
   - Implement audio ingestor with chunking
   - Create embedding pipeline for chunks
   - Create /api/ingest/audio endpoint
   - Add CRUD for transcript records

3. **User Story 3: Image OCR (P2)**
   - Setup Gemma4 vision client
   - Implement image processor
   - Create /api/ingest/image endpoint
   - Add CRUD for OCR result records

4. **User Story 4: File Management (P2)**
   - Implement file listing with filtering/sorting
   - Implement file deletion (atomic across storage locations)
   - Create /api/files endpoint
   - Add frontend Documents tab

5. **Cross-Cutting: Hybrid Search**
   - Implement Qdrant hybrid client
   - Implement RRF fusion
   - Add BM25 tokenization
   - Test cross-file-type retrieval

**Run `/speckit-tasks` to generate detailed task breakdown.**
