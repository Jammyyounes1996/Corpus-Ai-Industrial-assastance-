# Tasks: Remaining Workspace Tabs

**Input**: Design documents from `specs/005-remaining-tabs/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

## Mandatory Protocols (Apply to EVERY task)

1. **Graphify First**: Run `graphify query graphify-out/graph.json <symbol>` before reading any file to map imports, callers, and callees
2. **Think Before Code**: State the problem in one sentence → map what exists → identify the gap → write implementation plan as bullet points → then implement
3. **Backend/Frontend Split**: Never combine backend + frontend changes in one step. Sequence: (a) backend change → (b) verify backend → (c) frontend change → (d) verify frontend
4. **Verify After Each Task**: Read back the written file and confirm it matches the plan before moving to the next task

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Include exact file paths in descriptions

## Design Decisions (from research.md)

- **RAGAS metrics**: Only `faithfulness` + `answer_relevancy` (not context_precision/recall — require ground truth). Spec FR-010 aligned to 2 metrics per research decision R2.
- **Model selector**: RAGAS Evaluator includes Ollama model selector (FR-015) — judge model is user-switchable per session
- **File content serving**: `GET /api/files/{file_id}/content` via `FileResponse` with DB validation
- **Analysis tab data**: Fix existing `GET /api/chat/{chat_id}` to include `retrieved_context` (1-line change)
- **MIME type detection**: `mimetypes.guess_type()` from file extension, fallback `application/octet-stream`

---

## Phase 1: Setup

**Purpose**: Install new dependency and prepare project structure

- [ ] T001 Install `ragas` dependency and pin version in `requirements.txt`

  ```
  pip install ragas → note installed version → add exact pin to requirements.txt
  ```

- [ ] T002 [P] Create `backend/core/evaluation/` package directory with `__init__.py`

---

## Phase 2: Foundational (Backend Endpoints)

**Purpose**: All data the frontend needs must be available via API before any UI is written

**CRITICAL**: No frontend work (Phase 3+) can begin until ALL tasks in this phase pass verification

### Task Group 2A: Fix retrieved_context in message serialization

- [ ] T003 Add `retrieved_context` field to message dict builder in `backend/api/routes/chat.py`

  ```
  Graphify: query chat.py → find get_chat route → locate message dict builder (~line 140-150)
  Gap: dict includes thinking_steps but omits retrieved_context
  Fix: add "retrieved_context": msg.retrieved_context to the message dict
  Contract: GET /api/chat/{chat_id} → message objects include retrieved_context (JSON string, nullable)
  ```

- [ ] T004 Verify retrieved_context fix — call `GET /api/chat/{chat_id}` and confirm `retrieved_context` field appears in assistant messages

### Task Group 2B: File content serving endpoint

- [ ] T005 Add `GET /api/files/{file_id}/content` endpoint in `backend/api/routes/files.py`

  ```
  Graphify: query files.py → find existing routes → locate File model disk_path field
  Implementation:
  - Look up file in DB via existing crud.get_file()
  - Validate disk file exists at file.disk_path (return 404 if missing)
  - Detect MIME type via mimetypes.guess_type(file.disk_path), fallback application/octet-stream
  - Return FileResponse(path=file.disk_path, media_type=mime, filename=file.original_name)
  - Set Content-Disposition: inline for browser rendering
  Contract: see contracts/api.md GET /api/files/{file_id}/content
  ```

- [ ] T006 Verify file content endpoint — test with a known image file_id and confirm correct Content-Type header and file content returned

### Task Group 2C: RAGAS evaluation endpoints

- [ ] T007 [P] Create evaluation Pydantic schemas in `backend/schemas/evaluate.py`

  ```
  Models needed:
  - EvaluateRequest: chat_id (str), message_id (int)
  - EvaluationResponse: id, chat_id, message_id, faithfulness (float|None),
    answer_relevancy (float|None), model_used (str), created_at (datetime)
  - EvaluationListResponse: evaluations (list), total (int), limit (int), offset (int)
  - EvaluationListItem: extends EvaluationResponse + message_preview (str)
  Contract: see contracts/api.md POST /api/evaluate and GET /api/evaluations
  ```

- [ ] T008 [P] Add evaluation CRUD functions in `backend/database/crud.py`

  ```
  Graphify: query crud.py → understand session patterns → locate EvaluationResult model
  Functions needed (per data-model.md):
  - create_evaluation(session, *, chat_id, message_id, faithfulness, answer_relevancy, model_used) -> EvaluationResult
  - get_evaluations(session, *, chat_id=None, limit=50, offset=0) -> tuple[list[EvaluationResult], int]
  - get_evaluation_by_message(session, *, chat_id, message_id) -> EvaluationResult | None
  Follow existing async session patterns in the file
  ```

- [ ] T009 Create RAGAS evaluator service in `backend/core/evaluation/ragas_evaluator.py`

  ```
  Graphify: query settings.py → find OLLAMA_MODEL + OLLAMA_BASE_URL
  Implementation:
  - async function evaluate_message(question: str, answer: str, contexts: list[str]) -> dict
  - Configure Ollama as LLM judge via langchain-ollama (ChatOllama)
  - Run ragas evaluate() with faithfulness + answer_relevancy metrics only
  - Use asyncio.to_thread() to run sync ragas code (§8.1 async discipline)
  - Return {"faithfulness": float, "answer_relevancy": float}
  - Handle Ollama connection errors gracefully
  ```

- [ ] T010 Create evaluation router in `backend/api/routes/evaluate.py`

  ```
  Graphify: query chat.py → understand router patterns, error handling
  Endpoints:
  - POST /api/evaluate: validate chat+message exist, check no duplicate eval,
    extract question (user msg) + answer (assistant msg) + contexts (retrieved_context JSON),
    call ragas_evaluator, save via crud.create_evaluation, return 201
  - GET /api/evaluations: query params chat_id, limit, offset,
    join messages for message_preview (first 100 chars), return paginated list
  Error responses per contracts/api.md (404, 400, 409, 500)
  ```

- [ ] T011 Register evaluate router in `backend/main.py`

  ```
  Graphify: query main.py → find app.include_router calls
  Add: from backend.api.routes.evaluate import router as evaluate_router
  Add: app.include_router(evaluate_router, prefix="/api")
  ```

- [ ] T012 Verify evaluation endpoints — call `POST /api/evaluate` with a real chat_id that has messages containing retrieved_context, confirm scores are returned

**Checkpoint**: All 3 backend endpoint groups verified. Frontend work can begin.

---

## Phase 3: User Story 1 — Browse and Manage Documents (Priority: P1)

**Goal**: Fully functional file browser tab with filter, sort, upload, and delete

**Independent Test**: Navigate to Documents tab → verify grid loads from `GET /api/files` → upload a file → delete a file → filter by type → sort by name/date/size → verify empty state

### Frontend Type & Config Setup

- [ ] T013 [P] [US1] Add file list types in `frontend/src/types/files.ts`

  ```
  Types needed (from data-model.md Frontend Type Mappings):
  - FileItem: id, original_name, file_type, size_bytes, indexing_status, error_message,
    created_at, transcript_summary?, ocr_summary?
  - FileListResponse: files, total, limit, offset
  ```

- [ ] T014 [P] [US1] Add files and evaluate endpoints to `frontend/src/config.ts`

  ```
  Add to chatEndpoints (or new section):
  - listFiles: '/api/files'
  - fileContent: '/api/files/:fileId/content'
  - deleteFile: '/api/files/:fileId'
  - evaluate: '/api/evaluate'
  - evaluations: '/api/evaluations'
  ```

### Implementation

- [ ] T015 [US1] Create `frontend/src/components/tabs/DocumentsTab.tsx`

  ```
  Graphify: query WorkspaceContent → understand tab component pattern + props
  Component structure:
  - Fetch files from GET /api/files on mount (with filter/sort query params)
  - State: files[], loading, error, activeFilter ('all'|'pdf'|'audio'|'image'), sortBy
  - Filter chips: All / PDF / Audio / Image (query param: file_type)
  - Sort dropdown: Date desc / Name A-Z / Size (query params: sort_by, sort_order)
  - 3-column grid of file cards:
    - Each card: file type icon (lucide-react), filename, size (human-readable), date, status badge
    - Status badge: "Indexed" (green) or "Processing" (orange) or "Failed" (red)
    - Hover: show delete icon top-right
  - Delete: confirmation dialog → DELETE /api/files/{file_id} → refetch list
  - Upload button: trigger file picker → uploadFile() from fileUploadService → refetch list
  - Empty state: illustration + "No documents yet. Upload your first PDF, audio, or image."
  - Error state: connection error message + Retry button
  Acceptance: scenarios 1-6 from spec US1
  ```

- [ ] T016 [US1] Wire DocumentsTab into routing in `frontend/src/components/layout/WorkspaceContent.tsx`

  ```
  - Import DocumentsTab
  - Add case: activeTab === 'documents' → render <DocumentsTab />
  - Pass any needed props (activeSession for context if required)
  ```

- [ ] T017 [US1] Set `isPlaceholder: false` for documents tab in `frontend/src/components/tabs/WorkspaceData.ts`

- [ ] T018 [US1] Verify Documents tab — start dev server, navigate to Documents tab, confirm grid loads, filter/sort work, upload succeeds, delete with confirmation works, empty state shows when no files

**Checkpoint**: User Story 1 complete — Documents tab fully functional

---

## Phase 4: User Story 2 — OCR Image Gallery (Priority: P2)

**Goal**: Image thumbnail gallery with click-to-chat functionality

**Independent Test**: Navigate to OCR tab → verify 4-column image grid loads → hover shows "Open in Chat" overlay → click creates new chat with image attached → verify empty state

### Implementation

- [ ] T019 [US2] Create `frontend/src/components/tabs/OCRTab.tsx`

  ```
  Graphify: query fileUploadService → understand file types; query useChatSessions → understand chat creation
  Component structure:
  - Fetch files from GET /api/files?file_type=image on mount
  - 4-column grid of image thumbnails:
    - img src="/api/files/{file_id}/content" (via new content endpoint)
    - 200x200, object-fit: cover
    - Filename overlay at bottom
  - Hover state: "Open in Chat" overlay + tooltip with OCR text preview (from ocr_summary.text_preview)
  - Click handler:
    - Create new chat session via useChatSessions.createSession()
    - Attach image file_id to new chat
    - Pre-fill first message as "Tell me about this image"
    - Navigate to Chat tab (set activeTab to 'chat')
  - Empty state: "No images analyzed yet. Upload an image to get started."
  Acceptance: scenarios 1-4 from spec US2
  ```

- [ ] T020 [US2] Wire OCRTab into routing in `frontend/src/components/layout/WorkspaceContent.tsx`

  ```
  - Import OCRTab
  - Add case: activeTab === 'ocr' → render <OCRTab />
  - Pass sessions prop for chat creation, and onTabChange callback for navigation
  ```

- [ ] T021 [US2] Set `isPlaceholder: false` for ocr tab in `frontend/src/components/tabs/WorkspaceData.ts`

- [ ] T022 [US2] Verify OCR tab — start dev server, navigate to OCR tab with ingested images, confirm thumbnails load via content endpoint, hover shows overlay, click creates new chat and navigates to Chat tab, empty state shows when no images

**Checkpoint**: User Story 2 complete — OCR gallery with click-to-chat functional

---

## Phase 5: User Story 3 — Execution Trace Viewer (Priority: P3)

**Goal**: Analysis tab showing LangGraph execution trace, retrieved context, and model reasoning for the last conversation turn

**Independent Test**: Send a chat message that triggers retrieval → navigate to Analysis tab → verify all 3 sections display data from the last turn → verify empty state when no chat active

### Implementation

- [ ] T023 [US3] Create `frontend/src/components/tabs/AnalysisTab.tsx`

  ```
  Graphify: query useChatSessions → find active session state; query chat.ts types → ThinkingStep, SourceReference
  Component structure:
  - Fetch last assistant message from GET /api/chat/{backendChatId} for active session
  - Parse thinking_steps (JSON string → ThinkingStep[]) and retrieved_context (JSON string → SourceReference[])
  - Three vertically stacked sections:

  1. "LangGraph Execution Trace" section:
     - Vertical timeline of nodes from thinking_steps
     - Each node: name (type field), status badge (completed/failed/skipped),
       execution time (metadata.duration_ms), collapsible content
     - Color coding: completed=green, failed=red, skipped=gray

  2. "Retrieved Context" section:
     - Cards from retrieved_context array
     - Each card: source filename, chunk_index, similarity score (0-1 with color gradient),
       excerpt text (collapsed to 2 lines, expandable on click)

  3. "Model Reasoning Output" section:
     - Raw assistant message content in monospace block
     - Token count and generation time (if available from metadata)

  - Empty state: "No trace data available. Send a message in the Chat tab to see execution details."
  - No active chat: "Select or create a chat session to view analysis data."
  Acceptance: scenarios 1-5 from spec US3
  ```

- [ ] T024 [US3] Wire AnalysisTab into routing in `frontend/src/components/layout/WorkspaceContent.tsx`

  ```
  - Import AnalysisTab
  - Add case: activeTab === 'analysis' → render <AnalysisTab />
  - Pass activeSession prop (needed to get backendChatId for API call)
  ```

- [ ] T025 [US3] Set `isPlaceholder: false` for analysis tab in `frontend/src/components/tabs/WorkspaceData.ts`

- [ ] T026 [US3] Verify Analysis tab — start dev server, send a chat message with retrieval, navigate to Analysis tab, confirm all 3 sections render with real data, verify empty state when no conversations exist

**Checkpoint**: User Story 3 complete — Analysis tab shows real execution traces

---

## Phase 6: User Stories 4 & 5 — Tools Tab (Priority: P3)

**Goal**: Tools tab with RAGAS Evaluator and Audio Transcriber sub-views

**Independent Test**: Navigate to Tools tab → toggle between sub-views → run RAGAS evaluation on last chat → verify score cards display → switch to Audio Transcriber → verify transcript list loads → copy transcript

### Frontend Type Setup

- [ ] T027 [P] [US4] Add evaluation types in `frontend/src/types/evaluation.ts`

  ```
  Types needed (from data-model.md):
  - EvaluationResponse: id, chat_id, message_id, faithfulness (number|null),
    answer_relevancy (number|null), model_used, created_at
  - EvaluationListItem: extends EvaluationResponse + message_preview
  - EvaluationListResponse: evaluations, total, limit, offset
  ```

### Backend: Model selector support

- [ ] T027-B [US4] Backend — accept optional `judge_model` in `POST /api/evaluate` and add `model_used` column to EvaluationResult

  ```
  Part A — Add model_used column to EvaluationResult model in backend/database/models.py:
  - Add: model_used = mapped_column(String(200), nullable=True)
  - Create Alembic migration: alembic revision --autogenerate -m "add model_used to evaluation_results"
  - Run migration: alembic upgrade head

  Part B — Accept optional judge_model in evaluate endpoint:
  - Add optional "judge_model" field (str | None = None) to EvaluateRequest in backend/schemas/evaluate.py
  - In backend/api/routes/evaluate.py POST handler: pass judge_model to ragas_evaluator
  - In backend/core/evaluation/ragas_evaluator.py: accept optional model override param,
    use it instead of settings.OLLAMA_MODEL when provided
  - Store the actual model used in EvaluationResult.model_used via crud.create_evaluation()
  - If judge_model not provided, default to settings.OLLAMA_MODEL

  Resolves: model_used BLOCKER from analysis report
  ```

- [ ] T027-C [US4] Frontend — Ollama model scanner + selector dropdown in `frontend/src/components/tabs/ToolsTab.tsx`

  ```
  - On Tools tab mount, fetch GET http://localhost:11434/api/tags
    (Note: this goes directly to Ollama, not through backend — add Ollama proxy
    in vite.config.ts or call via a thin backend proxy endpoint)
  - Parse response → extract model name list from response.models[].name
  - Render dropdown labeled "Judge Model" above the "Run Evaluation" button
  - Pre-select the default model (match settings.OLLAMA_MODEL or first in list)
  - Store selected model in component state (persists for the session via React state)
  - Pass selected model as judge_model field in POST /api/evaluate request body
  - In evaluation history table, add "Model" column showing model_used for each past result
  ```

### Implementation

- [ ] T028 [US4] Create `frontend/src/components/tabs/ToolsTab.tsx`

  ```
  Graphify: query config.ts → find evaluate endpoints; query useChatSessions → active session
  Component structure:
  - Toggle at top: "RAGAS Evaluator" | "Audio Transcriber" (default: RAGAS)

  RAGAS Evaluator sub-view:
  - Model selector dropdown (from T027-C): fetches Ollama models, user picks judge model
  - "Run Evaluation" button → POST /api/evaluate with active chat's last assistant message + selected judge_model
  - Loading state: progress indicator with "Evaluating..." (10-60s expected)
  - Score cards: 2x1 grid (Faithfulness, Answer Relevancy)
    - Each card: metric name, score (0.0-1.0), color-coded gauge
      (green >= 0.7, yellow 0.4-0.7, red < 0.4), brief explanation
  - History table from GET /api/evaluations?chat_id={id}:
    - Columns: message preview, model used, faithfulness, answer_relevancy, timestamp
  - No active chat: "Send a message in the Chat tab first to enable evaluation."
  - Error state: "Evaluation failed" with details from error response

  Audio Transcriber sub-view:
  - Fetch files from GET /api/files?file_type=audio
  - List of audio files: filename, duration (from transcript_summary.duration_seconds),
    language, upload date
  - Expandable: full transcript text (scrollable)
  - Audio playback: <audio> element with src="/api/files/{file_id}/content"
  - "Copy transcript" button → clipboard API → confirmation toast
  - Empty state: "No audio files transcribed yet."

  Acceptance: scenarios 1-5 from spec US4 (includes model selector), scenarios 1-4 from spec US5
  ```

- [ ] T029 [US4] Wire ToolsTab into routing in `frontend/src/components/layout/WorkspaceContent.tsx`

  ```
  - Import ToolsTab
  - Add case: activeTab === 'tools' → render <ToolsTab />
  - Pass activeSession prop (needed for evaluate API call)
  ```

- [ ] T030 [US4] Set `isPlaceholder: false` for tools tab in `frontend/src/components/tabs/WorkspaceData.ts`

- [ ] T031 [US4] Verify Tools tab — start dev server, navigate to Tools tab, verify model selector dropdown loads Ollama models, select a model, run RAGAS evaluation on a real chat, confirm 2 score cards display and model_used appears in history, toggle to Audio Transcriber, confirm audio list and playback work, copy transcript

**Checkpoint**: User Stories 4 & 5 complete — Tools tab with both sub-views functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Integration, consistency, and final validation

- [ ] T032 Final cleanup of `frontend/src/components/layout/WorkspaceContent.tsx` — remove `getIconForTab` fallback function and unused PlaceholderView import once all tabs are wired

- [ ] T033 [P] Cross-tab state consistency — verify tab switching does not lose state, data fetching is cancelled on unmount (AbortController), no stale renders

- [ ] T034 [P] Empty states audit — verify all 4 tabs show correct empty state messages when: no files uploaded, no images ingested, no chat conversations, no evaluations run

- [ ] T035 Visual consistency audit — verify all new tab components match the established design system (warm palette, border radii, spacing, typography from existing ChatWorkspace and PlaceholderView CSS)

- [ ] T036 Final spec validation — re-read `specs/005-remaining-tabs/spec.md` and verify all 24 acceptance scenarios pass:

  ```
  US1 (Documents): 6 scenarios
  US2 (OCR): 4 scenarios
  US3 (Analysis): 5 scenarios
  US4 (RAGAS): 5 scenarios (includes model selector)
  US5 (Audio): 4 scenarios
  Total: 24 scenarios
  ```

- [ ] T037 Run `quickstart.md` verification sequence — execute all 3 curl verification commands and confirm responses match contracts/api.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (ragas install) — **BLOCKS all frontend work**
- **US1 Documents (Phase 3)**: Depends on Phase 2 completion (needs file content endpoint T005)
- **US2 OCR (Phase 4)**: Depends on Phase 2 (needs file content endpoint T005) + Phase 3 T013 (shared file types)
- **US3 Analysis (Phase 5)**: Depends on Phase 2 (needs retrieved_context fix T003)
- **US4+US5 Tools (Phase 6)**: Depends on Phase 2 (needs evaluate endpoint T010) + Phase 5 T027 (eval types)
- **Polish (Phase 7)**: Depends on all user story phases complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependencies on other stories
- **US2 (P2)**: Can start after Phase 2 — reuses file types from T013 (can run in parallel if types created first)
- **US3 (P3)**: Can start after Phase 2 — fully independent of other stories
- **US4+US5 (P3)**: Can start after Phase 2 — fully independent of other stories
- **US2, US3, US4+US5**: Can run in parallel after Phase 2 completes (if capacity allows)

### Within Each User Story

- Types/config before components
- Components before routing wires
- Routing wires before WorkspaceData updates
- All implementation before verification

### Parallel Opportunities (marked [P])

**Phase 1**: T001 and T002 can run in parallel
**Phase 2**: T007 and T008 can run in parallel (different files). T003 and T005 can run in parallel (different files).
**Phase 3**: T013 and T014 can run in parallel (different files)
**Phase 6**: T027 can run in parallel with T023-T026 (different files)
**Phase 7**: T033 and T034 can run in parallel

---

## Parallel Example: Phase 2 Backend

```bash
# Group 1 — independent backend changes (parallel):
Task T003: "Fix retrieved_context in backend/api/routes/chat.py"
Task T005: "Add file content endpoint in backend/api/routes/files.py"
Task T007: "Create schemas in backend/schemas/evaluate.py"
Task T008: "Add CRUD functions in backend/database/crud.py"

# Group 2 — depends on T007+T008 (sequential):
Task T009: "Create RAGAS evaluator in backend/core/evaluation/ragas_evaluator.py"
Task T010: "Create evaluate router in backend/api/routes/evaluate.py" (depends on T007, T008, T009)
Task T011: "Register router in backend/main.py" (depends on T010)

# Group 3 — verification (sequential after Group 1+2):
Task T004: "Verify retrieved_context fix"
Task T006: "Verify file content endpoint"
Task T012: "Verify evaluation endpoint"
```

## Parallel Example: Frontend Phases 3-6

```bash
# After Phase 2 backend is complete, frontend stories can proceed:

# Sequential per story (recommended for single developer):
Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US3) → Phase 6 (US4+US5)

# Or parallel (if multiple developers):
Developer A: Phase 3 (US1 Documents) + Phase 4 (US2 OCR)
Developer B: Phase 5 (US3 Analysis) + Phase 6 (US4+US5 Tools)
```

---

## Implementation Strategy

### MVP First (Documents Tab Only)

1. Complete Phase 1: Setup (ragas install)
2. Complete Phase 2: All 3 backend endpoints verified
3. Complete Phase 3: Documents tab (US1)
4. **STOP and VALIDATE**: Test Documents tab independently
5. Users can now browse, filter, upload, and delete documents

### Incremental Delivery

1. Setup + Foundational → Backend ready
2. Add US1 Documents → Test → **MVP deployed**
3. Add US2 OCR → Test → Image gallery live
4. Add US3 Analysis → Test → Execution traces visible
5. Add US4+US5 Tools → Test → RAGAS evaluation + transcripts
6. Polish → All 19 acceptance scenarios pass

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- RAGAS evaluation uses 2 metrics (faithfulness, answer_relevancy), not 4 — context_precision/recall require ground truth that doesn't exist in this system
- All frontend components follow the one-component-per-file pattern in `frontend/src/components/tabs/`
- The `fileUploadService.ts` already exists and handles uploads — Documents tab reuses it
- The `useChatSessions` hook provides active session state — Analysis and Tools tabs consume it
- Verify tests fail before implementing (if tests are added)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
