# Research: Remaining Workspace Tabs

**Date**: 2026-06-06 | **Feature**: [spec.md](spec.md)

## Research Items

### R1: How to serve file content (images/audio) to the frontend

**Decision**: Add `GET /api/files/{file_id}/content` endpoint using FastAPI `FileResponse`.

**Rationale**: Files are stored at `data/uploads/{uuid}.{ext}` but there is no static file mount and `disk_path` is not exposed in the API response. A dedicated endpoint provides:
- DB validation (file exists, belongs to user)
- Correct `Content-Type` headers based on `file_type` column
- Path traversal protection (only serves files found in DB)
- No need to expose internal disk paths to frontend

**Alternatives considered**:
- `StaticFiles` mount on `/uploads/` — exposes all files without auth, no DB validation
- Embedding base64 in API responses — wasteful for large images/audio, breaks caching

**Evidence**: `backend/api/routes/files.py` GET response excludes `disk_path`. `backend/database/models.py:104` stores `disk_path` per file. Vite proxy already forwards `/api` to backend.

---

### R2: RAGAS library integration with local Ollama

**Decision**: Use `ragas` library with only `faithfulness` and `answer_relevancy` metrics, powered by local Ollama via `langchain-ollama`.

**Rationale**:
- `context_precision` and `context_recall` require ground-truth reference answers that don't exist in this system
- `faithfulness` measures whether the answer is grounded in the retrieved context (needs: answer + contexts)
- `answer_relevancy` measures whether the answer addresses the question (needs: question + answer)
- Both metrics can use Ollama as the LLM judge through langchain-ollama, which is already installed

**Alternatives considered**:
- All 4 RAGAS metrics — requires ground-truth annotations, not feasible for runtime evaluation
- Custom scoring without ragas — loses the standardized metric framework and community validation
- Cloud LLM judge — adds external dependency and cost, violates offline-capable constraint

**Evidence**: `requirements.txt` has `langchain-ollama==0.2.3` but no `ragas`. `backend/database/models.py:208-211` has nullable `context_precision`/`context_recall` columns (will remain null). `backend/config/settings.py:41` has `OLLAMA_MODEL` for the judge model.

---

### R3: Analysis tab data source for thinking steps and retrieved context

**Decision**: Fix the existing `GET /api/chat/{chat_id}` endpoint to include `retrieved_context` in the message serialization, rather than creating a new endpoint.

**Rationale**:
- The DB column `messages.retrieved_context` (Text, nullable) already stores JSON from the stream endpoint (`backend/api/routes/chat.py:382-384`)
- The Pydantic `MessageSchema` at `backend/schemas/chat.py:63-69` already defines `retrieved_context: list[Source]`
- The gap is in the route handler: `chat.py:140-150` builds message dicts but omits `retrieved_context`
- Minimal fix: add the field to the dict builder (1 line)

**Alternatives considered**:
- New `GET /api/chat/{chat_id}/trace` endpoint — unnecessary since data already lives on messages
- Frontend-only state from streaming — thinking steps and sources are held in ephemeral `useChatSessions` state and lost on page refresh or tab switch

**Evidence**: `backend/api/routes/chat.py:140-150` — message dict includes `thinking_steps` but not `retrieved_context`. `backend/database/crud.py:336-358` — `update_message_content` persists both fields.

---

### R4: Frontend tab component architecture

**Decision**: One component file per tab under `frontend/src/components/tabs/`, routed by `WorkspaceContent.tsx`.

**Rationale**:
- Constitution §1.3 requires one concept per file
- Existing pattern: `WorkspaceContent.tsx` switches on `activeTab` and renders the matching component
- Tab definitions in `WorkspaceData.ts` already have `isPlaceholder: boolean` — flip to `false` as tabs are implemented
- Each tab manages its own data fetching; no shared tab state needed

**Evidence**: `frontend/src/components/layout/WorkspaceContent.tsx` — routing logic. `frontend/src/components/tabs/WorkspaceData.ts` — tab definitions with `isPlaceholder` flag.

---

### R5: MIME type detection for file content endpoint

**Decision**: Map the `file_type` column (pdf/audio/image) to MIME types using the file extension from `disk_path`.

**Rationale**:
- Files are stored as `data/uploads/{uuid}.{ext}` where ext is the original extension
- `file_type` gives the category; the extension gives the specific MIME type
- Python's `mimetypes.guess_type()` can derive MIME from the extension
- Fallback to `application/octet-stream` for unknown types

**Alternatives considered**:
- `python-magic` for content sniffing — already in requirements.txt but adds I/O overhead for known file types
- Hardcoded mapping — fragile if new file types are added

**Evidence**: `backend/database/models.py:104` — `disk_path` column stores the full path including extension. `requirements.txt` has `python-magic==0.4.27` as a fallback option.
