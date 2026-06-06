# Tasks: Phase 5 Known Limitations Fix

**Input**: Design documents from `/specs/006-known-limitations-fix/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/sse-done-usage.md, quickstart.md

**Tests**: Not explicitly requested. No test tasks included.

**Organization**: Tasks are grouped by implementation phase matching plan.md order (A→B→C→D). Phase A+B cover User Story 2 (LIM-2), Phase C covers User Story 1 (LIM-1), Phase D covers User Story 3 (LIM-3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Mandatory Protocol (applies to every task)

1. **Think first** — state the problem in one sentence before writing any code
2. **Run graphify** — map what exists before reading any source file
3. **Plan** — write implementation steps as bullet points
4. **Implement** — make the changes
5. **Verify** — confirm the change works before moving to next task
6. **Never combine backend + frontend** in one step

---

## Phase 1: Setup (No setup needed)

This feature modifies existing files only. No new project structure or dependencies required.

---

## Phase 2: Phase A — LIM-2 Backend (User Story 2, backend half)

**Goal**: Capture Ollama usage metadata in `answer_node` and propagate it through the SSE `done` event so the frontend can display real token counts and generation time.

**Independent Test**: Start backend, send a chat message via curl or browser, observe the SSE `done` event contains a `usage` field with `prompt_tokens`, `completion_tokens`, `total_tokens`, and `generation_time_ms`.

**Constraint**: Backward compatible — the `usage` field is optional. Existing clients that ignore it must not break.

- [X] T001 [US2] Extend `emit_done` to accept optional `usage` dict in `backend/agent/streaming.py`
  - **Problem**: `emit_done` currently only sends `message_id` and `chat_id`. It needs to accept and forward an optional `usage` dict.
  - **Protocol**: Run graphify to inspect `streaming.py` relationships, then read the file.
  - **Steps**:
    1. Add `usage: dict | None = None` parameter to `emit_done(message_id, chat_id, usage=None)` signature
    2. When `usage` is not `None`, include it in the SSE event data dict: `{"message_id": ..., "chat_id": ..., "usage": usage}`
    3. When `usage` is `None`, emit existing format (no `usage` key) — backward compatible
  - **Verify**: Confirm function signature change compiles, existing callers still work (they don't pass `usage`)

- [X] T002 [US2] Capture Ollama usage metadata in `answer_node` in `backend/agent/nodes/answer.py`
  - **Problem**: `answer_node` already tracks `start_time` and collects tokens but discards usage data after logging. It needs to compute usage metadata and pass it to `emit_done`.
  - **Protocol**: Run graphify to inspect `answer.py` relationships to `streaming.py`, then read both files.
  - **Steps**:
    1. After streaming completes in `answer_node`, compute `generation_time_ms = int((time.time() - start_time) * 1000)`
    2. Extract `eval_count` (completion tokens) and `prompt_eval_count` (prompt tokens) from the Ollama streaming response final chunk if available
    3. If Ollama provides `total_duration` (nanoseconds), convert: `generation_time_ms = total_duration // 1_000_000`
    4. Build usage dict: `{"prompt_tokens": prompt_eval_count, "completion_tokens": eval_count, "total_tokens": prompt_eval_count + eval_count, "generation_time_ms": generation_time_ms}`
    5. Pass `usage` dict to `emit_done` call
    6. If Ollama doesn't provide metadata, pass `usage=None` — graceful fallback
  - **Verify**: Start backend, send a chat message, inspect SSE `done` event in browser DevTools or curl — confirm `usage` field appears with real integer values

- [ ] T003 [US2] Verify Phase A end-to-end — SSE `done` event contains usage metadata
  - **Problem**: Need to confirm the full backend pipeline propagates usage data correctly.
  - **Steps**:
    1. Start backend: `cd backend && python -m uvicorn main:app --reload`
    2. Send a chat message via the frontend or curl
    3. Inspect the SSE stream — the final `done` event must contain: `{"message_id": "...", "chat_id": "...", "usage": {"prompt_tokens": N, "completion_tokens": N, "total_tokens": N, "generation_time_ms": N}}`
    4. Confirm backward compatibility: `message_id` and `chat_id` still present, `usage` is an extra field

**Checkpoint**: Backend SSE `done` event now includes real usage metadata. Phase B (frontend) can begin.

---

## Phase 3: Phase B — LIM-2 Frontend (User Story 2, frontend half)

**Goal**: Parse the `usage` field from the SSE `done` event and display real token counts and generation time in the Analysis tab instead of estimates.

**Independent Test**: Open Analysis tab after a real conversation, confirm token counts are non-zero integers without `~` prefix, and generation time reflects actual backend-measured duration.

**Depends on**: Phase 2 (Phase A) must be complete and verified.

- [X] T004 [US2] Extend `DoneEvent` type with optional `usage` field in `frontend/src/types/chat.ts`
  - **Problem**: The `DoneEvent` TypeScript type has no `usage` field. It needs one to type-check the new SSE data.
  - **Protocol**: Run graphify to inspect `chat.ts` relationships, then read the file.
  - **Steps**:
    1. Add a `UsageMetadata` interface (or inline type) with optional fields: `prompt_tokens?: number`, `completion_tokens?: number`, `total_tokens?: number`, `generation_time_ms?: number`
    2. Add `usage?: UsageMetadata` to the `DoneEvent` data shape (the existing `data` field that holds `message_id` and `chat_id`)
    3. Ensure all existing code that accesses `DoneEvent.data.message_id` still compiles
  - **Verify**: `npm run build` (or `tsc --noEmit`) passes with no type errors

- [X] T005 [US2] Update `validateDoneEvent` to extract `usage` in `frontend/src/services/chatStreamParser.ts`
  - **Problem**: `validateDoneEvent` parses the SSE `done` event data but doesn't extract the `usage` field.
  - **Protocol**: Run graphify to inspect `chatStreamParser.ts` relationships, then read the file.
  - **Steps**:
    1. After validating `message_id` and `chat_id`, check if `data.usage` exists
    2. If present, include it in the returned `DoneEvent` object
    3. If absent, omit it (don't add a default) — keeps backward compatibility
  - **Verify**: Type-check passes; existing done event (without `usage`) still parses correctly

- [X] T006 [US2] Display real metrics in `AnalysisTab` replacing estimates in `frontend/src/components/tabs/AnalysisTab.tsx`
  - **Problem**: `AnalysisTab` estimates token count via `Math.round(content.length / 4)` and generation time via thinking step durations. Real values from `usage` should replace these when available.
  - **Protocol**: Run graphify to inspect `AnalysisTab.tsx` relationships, then read the file.
  - **Steps**:
    1. Access `usage` from the done event data (already stored in component state or conversation store)
    2. For token count: when `usage.total_tokens` exists, display it directly; otherwise fall back to `Math.round(content.length / 4)` prefixed with `~`
    3. For generation time: when `usage.generation_time_ms` exists, display it as seconds (`(ms / 1000).toFixed(1) + 's'`); otherwise fall back to thinking step sum prefixed with `~`
    4. Remove `~` prefix when displaying real values — it only appears on estimates
  - **Verify**: Open Analysis tab after a real conversation — confirm token counts are real integers (no `~`), generation time matches backend measurement. Then test fallback: stop backend mid-stream, confirm estimated values appear with `~` prefix.

**Checkpoint**: LIM-2 complete. Real token counts and generation time display in Analysis tab with fallback to estimates.

---

## Phase 4: Phase C — LIM-1 OCR Image Attachment (User Story 1)

**Goal**: When the user clicks an OCR image to "Open in Chat", the image is formally attached to the chat message (not just filename text), so the backend can process the actual file.

**Independent Test**: Upload image in OCR tab, process it, click image to open in chat. Verify image appears as attachment thumbnail, and AI references actual image content in its response.

**Depends on**: Nothing — can be verified independently.

- [X] T007 [US1] Modify `handleOpenInChat` to fetch image Blob and attach as File in `frontend/src/components/tabs/OCRTab.tsx`
  - **Problem**: `handleOpenInChat` creates a text-only message with the filename. It needs to fetch the actual image binary and attach it as a `File` object so the backend receives the real file.
  - **Protocol**: Run graphify to inspect `OCRTab.tsx` relationships to `chat.ts` types and file API, then read the file.
  - **Steps**:
    1. Inside `handleOpenInChat`, before calling `appendUserMessage`:
       - Build URL: `/api/files/${file.id}/content`
       - `const response = await fetch(url)`
       - `const blob = await response.blob()`
       - `const fileObj = new File([blob], file.original_name, { type: file.mime_type })`
    2. Check size: `if (fileObj.size === 0) { console.warn(...); /* fall back */ }`
    3. Create `AttachedFile` using the existing `createAttachedFile` utility (or inline the attachment object matching the existing type)
    4. Pass the attachment as the third argument to `appendUserMessage(message, chatId, [attachment])`
    5. Keep the text message: `"Tell me about this image: {original_name}"`
    6. Wrap the fetch in try/catch: if fetch fails, `console.warn('Failed to attach image:', error)` and proceed with text-only message (current behavior)
  - **Verify**: Upload image in OCR tab, process it, click "Open in Chat". Confirm: (1) image thumbnail appears in chat message attachment tray, (2) AI response describes actual image content, (3) if file is deleted from storage before clicking, graceful fallback to text-only message.

**Checkpoint**: LIM-1 complete. OCR images open in chat with real file attachment and graceful fallback.

---

## Phase 5: Phase D — LIM-3 CSS Split (User Story 3)

**Goal**: Extract audio transcriber styles from `ToolsTab.css` (460 lines, over 400-line cap) into `AudioTranscriber.css`, reducing `ToolsTab.css` to ~293 lines. Zero behavior change.

**Independent Test**: Open Tools tab, navigate to Audio Transcriber — verify all elements render identically. Confirm `ToolsTab.css` is under 400 lines.

**Depends on**: Nothing — pure CSS refactor.

- [X] T008 [P] [US3] Create `AudioTranscriber.css` with extracted `.tools-audio__*` styles in `frontend/src/components/tabs/AudioTranscriber.css`
  - **Problem**: `ToolsTab.css` is 460 lines (over 400-line constitution cap). Audio transcriber styles (lines 294-460, ~167 lines) need to be extracted.
  - **Protocol**: Run graphify to inspect `ToolsTab.css` relationships, then read the file.
  - **Steps**:
    1. Read `ToolsTab.css` lines 294-460 (all `.tools-audio__*` rules)
    2. Create new file `frontend/src/components/tabs/AudioTranscriber.css`
    3. Copy the extracted CSS rules verbatim — no class name changes, no content changes
  - **Verify**: New file exists with ~167 lines of `.tools-audio__*` rules

- [X] T009 [US3] Import `AudioTranscriber.css` in `AudioTranscriber.tsx` and remove extracted styles from `ToolsTab.css`
  - **Problem**: The new `AudioTranscriber.css` needs to be imported by its component, and the old styles need to be removed from `ToolsTab.css`.
  - **Protocol**: Read `AudioTranscriber.tsx` and `ToolsTab.css`.
  - **Steps**:
    1. Add `import './AudioTranscriber.css'` to `AudioTranscriber.tsx` imports section
    2. Delete lines 294-460 from `ToolsTab.css` (the `.tools-audio__*` rules)
    3. Verify `ToolsTab.css` is now ~293 lines (under 400-line cap)
  - **Verify**: Run `npm run build` — must pass. Visual inspection: open Tools tab → Audio Transcriber section, confirm identical rendering. Run `git diff --stat` — confirm only file additions/deletions, no content changes to CSS rules.

**Checkpoint**: LIM-3 complete. `ToolsTab.css` under 400 lines. No visual regression.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all limitations.

- [ ] T010 Run quickstart.md validation — verify all three LIMs work end-to-end
  - **Steps**:
    1. Follow LIM-1 steps from `quickstart.md`: OCR image → Open in Chat → verify attachment
    2. Follow LIM-2 steps: submit analysis query → verify real token count and generation time
    3. Follow LIM-3 steps: open Tools tab → verify Audio Transcriber renders identically
    4. Confirm `ToolsTab.css` line count is under 400
  - **Verify**: All quickstart.md checks pass

- [ ] T011 Constitution compliance check — verify all files under 400 lines, one concept per file
  - **Steps**:
    1. Count lines in `ToolsTab.css` — must be under 400
    2. Count lines in `AudioTranscriber.css` — must be under 400
    3. Count lines in all modified files — must be under 400
    4. Verify one concept per file: `AudioTranscriber.css` has only audio transcriber styles
  - **Verify**: All constitution checks pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 2 (Phase A — LIM-2 backend)**: No dependencies — start immediately
- **Phase 3 (Phase B — LIM-2 frontend)**: Depends on Phase 2 completion — needs backend emitting `usage`
- **Phase 4 (Phase C — LIM-1)**: No dependencies — independent of LIM-2
- **Phase 5 (Phase D — LIM-3)**: No dependencies — pure CSS refactor
- **Phase 6 (Polish)**: Depends on all phases being complete

### User Story Dependencies

- **User Story 1 (P1 — LIM-1 OCR attachment)**: Independent — Phase 4
- **User Story 2 (P2 — LIM-2 real metrics)**: Backend (Phase 2) → Frontend (Phase 3) — sequential within story
- **User Story 3 (P3 — LIM-3 CSS split)**: Independent — Phase 5

### Within Each Phase

- T001 before T002 (emit_done signature must change before answer_node calls it)
- T004 before T005 before T006 (type → parser → display — sequential chain)
- T008 before T009 (create file before importing/removing)

### Parallel Opportunities

- Phase 4 (C) and Phase 5 (D) can run in parallel with Phase 2 (A)
- T008 and T009 must be sequential (same files involved)
- T004, T005, T006 must be sequential (dependency chain)

---

## Parallel Example: Phase A + Phase C + Phase D

```text
# These can all start simultaneously:
Agent 1: T001 → T002 → T003 (Phase A — LIM-2 backend)
Agent 2: T007 (Phase C — LIM-1 OCR attachment)
Agent 3: T008 → T009 (Phase D — LIM-3 CSS split)

# Then after Phase A completes:
Agent 1: T004 → T005 → T006 (Phase B — LIM-2 frontend)

# Final validation:
Any agent: T010 → T011 (Polish)
```

---

## Implementation Strategy

### MVP First (User Story 1 — LIM-1 only)

1. Complete Phase 4 (Phase C): T007
2. **STOP and VALIDATE**: OCR image attaches to chat message
3. Deploy/demo if ready

### Recommended Order (matches plan.md)

1. Phase 2 (A): T001 → T002 → T003 — Backend usage metadata
2. Phase 3 (B): T004 → T005 → T006 — Frontend display
3. Phase 4 (C): T007 — OCR image attachment
4. Phase 5 (D): T008 → T009 — CSS split
5. Phase 6: T010 → T011 — Final validation

### Incremental Delivery

1. Complete Phase A → test backend SSE output
2. Complete Phase B → test real metrics in Analysis tab
3. Complete Phase C → test OCR image attachment
4. Complete Phase D → test CSS split, no visual regression
5. Run Phase 6 validation — all quickstart checks pass

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- User Story 2 spans two phases (A: backend, B: frontend) — never combine in one step
- User Stories 1 and 3 are fully independent — can run in parallel
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
- Constitution: all files must stay under 400 lines, one concept per file
- SSE contract: `usage` field is optional — backward compatible
