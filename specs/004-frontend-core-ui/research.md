# Research: Frontend Core UI Contract Verification

## Decision: Actual frontend framework/build tool

**Chosen**: Current repository frontend is Streamlit/Python under `frontend/`; Phase 4 React implementation has no existing `frontend/package.json`, `frontend/src`, Vite config, TypeScript config, or JavaScript build tool to reuse.

**Rationale**: Repository inspection found `frontend/app.py` importing Streamlit modules and no React project files. This means Phase 4 cannot assume an existing React/Vite app and must either create one deliberately or revise scope before implementation.

**Alternatives considered**:
- Reuse existing React/Vite setup: rejected because no React/Vite setup exists in the repository.
- Implement Phase 4 in Streamlit: rejected because the Phase 4 plan explicitly requires React under `frontend/src` and not Streamlit.

**Implementation impact**:
- A React project scaffold and dependency setup is required before React UI implementation.
- Existing Streamlit files under `frontend/` must not be treated as React source files.
- CORS must be revisited because backend currently allows `http://localhost:8501`, matching Streamlit rather than a typical React dev server.

## Decision: Actual styling approach

**Chosen**: Existing frontend styling is Streamlit plus plain CSS loaded from `frontend/styles/main.css` through `frontend/styles/load_css.py`.

**Rationale**: Repository inspection found a Streamlit CSS injection helper and one CSS file. No Tailwind, CSS Modules, styled-components, MUI, Chakra, or other frontend styling framework exists.

**Alternatives considered**:
- Add Tailwind: rejected because no Tailwind setup exists and the plan forbids heavy/new styling systems without approval.
- Add a component framework: rejected because it would conflict with the minimal dependency and existing-convention requirements.

**Implementation impact**:
- If React is created, prefer plain CSS/design tokens under `frontend/src/styles` unless the user approves another styling system.
- Existing Streamlit CSS can inform visual tokens but should not be imported as a React implementation contract without review.

## Decision: Actual test runner

**Chosen**: Current repository test tooling is Python-based: `pytest`, `pytest-asyncio`, and `pytest-cov` are present in `requirements.txt`; no frontend JavaScript test runner was found.

**Rationale**: No `package.json`, Vitest, Jest, Playwright, or Testing Library setup exists. The only confirmed test tools are Python tools.

**Alternatives considered**:
- Reuse Vitest: rejected because no Vitest setup exists.
- Reuse Jest/React Testing Library: rejected because no JavaScript frontend setup exists.

**Implementation impact**:
- React implementation will require an explicit choice and installation of frontend test tooling.
- Planning should not claim frontend tests can run until a JavaScript build/test setup exists.

## Decision: Actual markdown rendering choice

**Chosen**: No existing React markdown renderer is available; use `react-markdown` with `remark-gfm` only if the React project is created and the dependency addition is approved.

**Rationale**: Current frontend is Streamlit and does not provide a reusable React markdown renderer. The Phase 4 UI requires markdown answers and code blocks, but dependencies cannot be assumed before the React project exists.

**Alternatives considered**:
- Use unsafe raw HTML rendering: rejected because the plan forbids unsafe raw HTML unless sanitization is added and approved.
- Build a custom markdown parser: rejected because it is out of Phase 4 scope and higher risk than a maintained renderer.

**Implementation impact**:
- Markdown rendering code must be deferred until React dependency setup is explicit.
- Code block styling and copy behavior should be implemented as React markdown component mappings after renderer selection.

## Decision: Actual chat streaming format

**Chosen**: Backend-compatible chat streaming is `POST /api/chat/{chat_id}/stream` returning Server-Sent Events through `sse-starlette` `EventSourceResponse`.

**Rationale**: `backend/api/routes/chat.py` defines `@router.post("/chat/{chat_id}/stream")`, validates `StreamRequest`, and yields SSE events with `event` names and JSON `data` payloads. This does not match the previously assumed `POST /api/chat/stream` path.

**Alternatives considered**:
- Use `POST /api/chat/stream`: rejected because that route does not exist.
- Use EventSource GET: rejected because the backend stream route is POST and accepts a JSON request body.

**Implementation impact**:
- Frontend must create or select a chat first using `POST /api/chats` and then stream to `/api/chat/{chat_id}/stream`.
- Stream parsing must parse SSE frame delimiters, not arbitrary NDJSON chunks.
- Contract docs must flag the path mismatch before implementation.

## Decision: Actual upload flow

**Chosen**: Backend upload/ingestion is split by file type: `POST /api/ingest/pdf`, `POST /api/ingest/audio`, and `POST /api/ingest/image`, each accepting one multipart `file` field.

**Rationale**: `backend/api/routes/ingest.py` defines three upload endpoints with content-type validation and returns ingestion results containing `file_id`, `filename`, `status`, and `size_bytes` plus type-specific fields.

**Alternatives considered**:
- Use a generic upload endpoint: rejected because no generic upload endpoint exists.
- Upload multiple files in one request: rejected because the existing endpoints accept a single `UploadFile` parameter.

**Implementation impact**:
- Frontend must route each selected file to the matching endpoint by MIME type.
- Attachment references passed to chat must be backend `file_id` strings from successful upload responses.
- Partial upload failures must be surfaced per file; failed files must not be included in `attached_files`.

## Decision: Actual status flow

**Chosen**: Use `GET /health` for backend dependency status and optionally `GET /api/models` for available Ollama model list; unavailable fields must render as `Unknown` or `Unavailable`.

**Rationale**: `backend/main.py` defines `/health` with `status`, `version`, `database`, `qdrant`, and `ollama`. `backend/api/routes/models.py` defines `/api/models` with model list data. There is no single status endpoint exposing provider, active model, RAG enabled, OCR readiness, or GPU.

**Alternatives considered**:
- Invent a richer frontend status object: rejected because fake status values are forbidden.
- Treat `/api/models` as full system status: rejected because it only reports Ollama model list availability.

**Implementation impact**:
- Header/status UI can show backend, Qdrant, database, and Ollama from `/health`.
- Model/provider/RAG/OCR/GPU fields require fallback labels unless backend is extended.
- Frontend must gracefully handle network failure as disconnected/unavailable.

## Decision: Whether new dependencies are required

**Chosen**: Yes, new frontend dependencies are required if Phase 4 remains a React implementation, because no JavaScript frontend project currently exists.

**Rationale**: Repository inspection found no `frontend/package.json`, no `frontend/src`, no Vite/TypeScript config, and no JavaScript test setup. React, build tooling, markdown rendering, icons, and tests are therefore not already available.

**Alternatives considered**:
- No new dependencies: rejected because React implementation cannot proceed without a React toolchain.
- Reuse Python Streamlit dependencies: rejected because they do not satisfy the Phase 4 React UI plan.

**Implementation impact**:
- Dependency additions must be explicit and reviewed before implementation.
- `package.json` and the React source tree must be created deliberately, not assumed.
- Build/test commands must be documented after toolchain selection.

## Decision: Whether any backend contract mismatch exists

**Chosen**: Backend contract mismatches exist and must be documented before implementation.

**Rationale**: The expected `/api/chat/stream` endpoint does not exist. The actual route is `/api/chat/{chat_id}/stream` and requires a chat UUID. Upload is not a generic attachment endpoint; it is split by file type. Status data is limited. CORS currently allows `http://localhost:8501`, not a React dev-server origin.

**Alternatives considered**:
- Ignore mismatches and adapt frontend silently: rejected because the plan requires explicit stop/report behavior for contract mismatches.
- Mock missing fields in frontend: rejected by the no-mock/no-fake API rule.

**Implementation impact**:
- `chat-stream.md`, `file-upload.md`, and `status.md` must be treated as the source of truth for Phase 4 integration.
- Implementation should not start until the user accepts using the real contracts or approves backend contract changes.
