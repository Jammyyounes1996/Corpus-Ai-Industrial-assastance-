# Implementation Plan: Remaining Workspace Tabs

**Branch**: `specs/005-remaining-tabs` | **Date**: 2026-06-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/005-remaining-tabs/spec.md`

## Summary

Implement four workspace tabs (Documents, OCR, Analysis, Tools) that provide browsing, inspection, and evaluation capabilities for the industrial AI assistant's knowledge base. The backend needs three new endpoints (file content serving, chat message fix, RAGAS evaluation) while the frontend replaces placeholder views with real React components consuming existing and new API data.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript 5.x (frontend)  
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 async, React 18, Vite 4, lucide-react, ragas (new)  
**Storage**: SQLite via aiosqlite, Qdrant vector DB, disk files at `data/uploads/`  
**Testing**: pytest + pytest-asyncio (backend), vitest (frontend)  
**Target Platform**: Local desktop (Windows 11), localhost:8001 (backend), localhost:5173 (frontend)  
**Project Type**: Web application (FastAPI + React SPA)  
**Performance Goals**: Tab render <500ms, file content endpoint <200ms, RAGAS evaluation <60s  
**Constraints**: Offline-capable (Ollama local), single user, SQLite single-writer  
**Scale/Scope**: ~100 files, ~50 chats, single concurrent user

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| §1.1 Functions <=50 lines | PASS | All new functions designed to stay under 30 lines |
| §1.3 File length <=400 lines | PASS | Each tab component in its own file; backend routes split by domain |
| §3.1 Type hints on all public functions | PASS | Full annotations planned for all new endpoints and components |
| §3.2 Docstrings on public APIs | PASS | Google-style docstrings on all new route handlers |
| §4.1 Custom exceptions | PASS | Will use existing AppError hierarchy |
| §5.1 Library selection (ragas) | PASS | Active maintenance, MIT license, Python 3.11+ compatible, documented |
| §5.2 Version pinning | PASS | ragas will be pinned to exact version |
| §6.2 Config via env vars | PASS | No new config needed beyond existing settings |
| §8.1 Async discipline | PASS | All new endpoints async; RAGAS uses asyncio.to_thread for sync calls |
| §10.3 API calls via service layer | PASS | Frontend uses centralized API client, not scattered fetch calls |
| §14.1 Input validation via Pydantic | PASS | All new endpoints use Pydantic request/response models |

No constitution violations. No complexity justifications needed.

## Project Structure

### Documentation (this feature)

```text
specs/005-remaining-tabs/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api.md           # New endpoint contracts
└── tasks.md             # Phase 2 output (from /speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── api/routes/
│   ├── files.py          # MODIFY: add GET /api/files/{file_id}/content
│   ├── chat.py           # MODIFY: include retrieved_context in message serialization
│   └── evaluate.py       # NEW: POST /api/evaluate, GET /api/evaluations
├── schemas/
│   ├── chat.py           # EXISTS: MessageSchema already has retrieved_context
│   └── evaluate.py       # NEW: EvaluateRequest, EvaluateResponse schemas
├── core/
│   └── evaluation/
│       └── ragas_evaluator.py  # NEW: RAGAS evaluation logic
└── database/
    ├── models.py         # EXISTS: EvaluationResult model ready
    └── crud.py           # MODIFY: add evaluation CRUD functions

frontend/
├── src/
│   ├── components/
│   │   ├── tabs/
│   │   │   ├── DocumentsTab.tsx   # NEW
│   │   │   ├── OCRTab.tsx         # NEW
│   │   │   ├── AnalysisTab.tsx    # NEW
│   │   │   └── ToolsTab.tsx       # NEW
│   │   └── layout/
│   │       └── WorkspaceContent.tsx  # MODIFY: route to real tab components
│   ├── services/
│   │   └── filesService.ts        # NEW: API client for /api/files
│   ├── hooks/
│   │   └── useFiles.ts            # NEW: file list data fetching hook
│   └── types/
│       ├── files.ts               # NEW: file response types
│       └── evaluation.ts          # NEW: evaluation response types
└── tests/
```

**Structure Decision**: Web application pattern (backend/ + frontend/) already established. New code follows existing conventions: backend routes in `api/routes/`, schemas in `schemas/`, business logic in `core/`. Frontend follows component-per-file in `components/tabs/`.

## Implementation Phases

### Phase 1: Backend Fixes & New Endpoints

**Task 1.1**: Fix `GET /api/chat/{chat_id}` to include `retrieved_context` in message serialization.
- The Pydantic `MessageSchema` at `backend/schemas/chat.py:63` already defines `retrieved_context: list[Source]`
- The route handler at `backend/api/routes/chat.py:140-150` builds dicts manually and omits `retrieved_context`
- Fix: add `"retrieved_context": msg.retrieved_context` to the message dict builder

**Task 1.2**: Add `GET /api/files/{file_id}/content` endpoint.
- Lookup file in DB via `crud.get_file()` → validate file exists on disk → return `FileResponse`
- Content-type detection: map `file_type` column to MIME types (pdf→application/pdf, image→image/*, audio→audio/*)
- Uses `fastapi.responses.FileResponse` for efficient streaming with correct headers

**Task 1.3**: Add RAGAS evaluation endpoints.
- `POST /api/evaluate` — accepts `{chat_id, message_id}`, runs faithfulness + answer_relevancy
- `GET /api/evaluations` — lists evaluation history with optional chat_id filter
- Install `ragas` library, use Ollama as LLM judge via langchain-ollama integration
- Save results to existing `EvaluationResult` table (context_precision/recall left null per decision)

### Phase 2: Documents Tab

**Task 2.1**: Replace placeholder with `DocumentsTab` component.
- Fetches from `GET /api/files` with filter/sort query params
- Renders 3-column grid of file cards (filename, type icon, size, date, status badge)
- Filter chips: All / PDF / Audio / Image
- Sort dropdown: Date (desc) / Name (A-Z) / Size
- Upload button triggers existing `fileUploadService`
- Delete with confirmation dialog using existing `DELETE /api/files/{file_id}`
- Empty state when no files

### Phase 3: OCR & Audio Tab

**Task 3.1**: OCR image gallery.
- Filters files by type=image from same `/api/files` endpoint
- 4-column grid, images loaded via `GET /api/files/{file_id}/content`
- Click opens detail panel showing full OCR extracted text
- "Open in Chat" action creates new chat session with image pre-attached

**Task 3.2**: Audio transcript viewer (sub-view of OCR tab or accessible from Documents).
- Filters files by type=audio
- Lists audio files with expandable transcript text
- Audio playback via `<audio>` element with `/api/files/{file_id}/content` src

### Phase 4: Analysis Tab

**Task 4.1**: Execution trace viewer.
- Fetches active chat's messages from `GET /api/chat/{chat_id}`
- Parses last assistant message's `thinking_steps` JSON → renders vertical timeline
- Each node shows: name, status badge, duration_ms, collapsible content
- Parses `retrieved_context` JSON → renders source chunk cards with score + excerpt
- Model reasoning output section shows raw assistant message content in monospace

### Phase 5: Tools Tab (RAGAS Evaluator)

**Task 5.1**: RAGAS evaluator UI.
- Toggle between "RAGAS Evaluator" and "Audio Transcriber" sub-views
- Evaluator: "Run Evaluation" button → calls `POST /api/evaluate` with active chat's last message
- Loading state with progress indicators (10-60s expected)
- Score cards: 2 metrics (Faithfulness, Answer Relevancy) as 0.0-1.0 gauges, color-coded
- History table from `GET /api/evaluations`

**Task 5.2**: Audio transcriber sub-view.
- Reuses audio file list + transcript expansion from Phase 3
- Copy transcript button

### Phase 6: Integration & Polish

**Task 6.1**: Wire tab routing — update `WorkspaceContent.tsx` to route to real components.
**Task 6.2**: Cross-tab state consistency and empty states.
**Task 6.3**: Final spec validation against all 19 acceptance criteria.

## Complexity Tracking

No constitution violations requiring justification.
