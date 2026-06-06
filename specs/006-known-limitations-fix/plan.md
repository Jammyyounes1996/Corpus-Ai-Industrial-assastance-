# Implementation Plan: Phase 5 Known Limitations Fix

**Branch**: `specs/005-remaining-tabs` | **Date**: 2026-06-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/006-known-limitations-fix/spec.md`

## Summary

Fix three accepted limitations from Phase 5: (LIM-1) OCR tab formally attaches images to chat messages so the backend can process the actual file, (LIM-2) display real token counts and generation time from the backend instead of estimates, and (LIM-3) reduce `ToolsTab.css` below 400 lines by extracting audio transcriber styles to a component-specific CSS file.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript + React (frontend)
**Primary Dependencies**: FastAPI, sse-starlette, Ollama, React, Vite
**Storage**: SQLite (existing — no schema changes)
**Testing**: pytest (backend), manual verification (frontend)
**Target Platform**: Local development (RTX 3060 GPU)
**Project Type**: Web application (FastAPI backend + React frontend)
**Performance Goals**: No regression — SSE stream latency unchanged
**Constraints**: No new dependencies, backward-compatible SSE contract, backward-compatible API
**Scale/Scope**: 3 targeted fixes, ~10 files modified

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Article | Gate | Status |
|---------|------|--------|
| §1.1 Clean Code | Functions ≤ 50 lines, no magic numbers | PASS — all changes are small, focused |
| §1.3 File Organization | One concept per file, ≤ 400 lines | PASS — LIM-3 specifically addresses this |
| §2.1 Python Naming | lower_snake_case for functions | PASS — no naming violations |
| §3.1 Type Hints | Full annotations on public functions | PASS — new types will be annotated |
| §8.2 Streaming | SSE with final `done` event | PASS — extending existing `done` event |
| §9.4 Experimental Phase | Tests optional when marked in tasks.md | PASS — will mark in tasks.md |

### Post-Phase 1 Re-check

| Check | Result |
|-------|--------|
| No new files over 400 lines | PASS — `AudioTranscriber.css` will be ~167 lines |
| No new dependencies | PASS — uses existing browser APIs (Blob, File) |
| SSE contract backward compatible | PASS — `usage` is optional |

## Project Structure

### Documentation (this feature)

```text
specs/006-known-limitations-fix/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── sse-done-usage.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── agent/
│   ├── nodes/
│   │   └── answer.py              # LIM-2: capture usage metadata
│   └── streaming.py               # LIM-2: extend emit_done with usage
├── api/
│   └── routes/
│       └── chat.py                # LIM-2: propagate usage to SSE
└── schemas/
    └── chat.py                    # Existing — no changes needed

frontend/src/
├── components/
│   └── tabs/
│       ├── OCRTab.tsx             # LIM-1: attach image to chat message
│       ├── AnalysisTab.tsx        # LIM-2: display real metrics
│       ├── ToolsTab.css           # LIM-3: reduce by extracting audio styles
│       └── tools/
│           ├── AudioTranscriber.tsx  # LIM-3: add CSS import
│           └── AudioTranscriber.css  # LIM-3: NEW — extracted styles
├── services/
│   └── chatStreamParser.ts       # LIM-2: parse usage from done event
└── types/
    └── chat.ts                    # LIM-2: extend DoneEvent type
```

**Structure Decision**: Web application structure — backend + frontend. All changes fit within existing directory structure. One new file (`AudioTranscriber.css`).

## Complexity Tracking

No constitution violations. No entries needed.

## Implementation Order

### Phase A: LIM-2 — Backend First (enables frontend testing)

**Rationale**: Backend must emit usage metadata before frontend can consume it.

**Step A1**: Extend `emit_done` in `backend/agent/streaming.py`
- Add optional `usage` parameter: `dict | None = None`
- Include `usage` in the SSE `done` event data when provided
- Backward compatible: omit `usage` key when `None`

**Step A2**: Capture Ollama usage in `backend/agent/nodes/answer.py`
- The `answer_node` function already tracks `start_time` and collects tokens
- After streaming completes, compute `generation_time_ms` from `start_time`
- Count collected tokens for `completion_tokens`
- Ollama's `/api/generate` response includes `eval_count` and `prompt_eval_count` — capture these if available from the OllamaClient stream
- Pass usage dict to `emit_done`

**Step A3**: Verify backend SSE output
- Run backend, send a chat message, observe SSE `done` event
- Confirm `usage` field appears with real values

### Phase B: LIM-2 — Frontend Display

**Step B1**: Extend `DoneEvent` type in `frontend/src/types/chat.ts`
- Add optional `usage` field to `DoneEvent.data`:
  ```typescript
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
    generation_time_ms?: number;
  }
  ```

**Step B2**: Update `validateDoneEvent` in `frontend/src/services/chatStreamParser.ts`
- Extract optional `usage` from done event data
- Pass through to `DoneEvent` return value

**Step B3**: Update display in `frontend/src/components/tabs/AnalysisTab.tsx`
- Replace `Math.round(content.length / 4)` with real `usage.total_tokens` when available
- Replace `thinkingSteps.reduce(sum durations)` with real `usage.generation_time_ms` when available
- Fall back to estimated values with `~` prefix when `usage` is absent
- Remove `~` prefix when displaying real values

**Step B4**: Verify LIM-2 end-to-end
- Submit analysis query, confirm real token count and generation time display
- Test fallback: stop backend mid-stream, confirm estimated values appear

### Phase C: LIM-1 — OCR Image Attachment (frontend only)

**Step C1**: Modify `handleOpenInChat` in `frontend/src/components/tabs/OCRTab.tsx`
- Before creating the chat message, fetch the image:
  ```
  1. Build URL: /api/files/{file.id}/content
  2. fetch() → response.blob()
  3. new File([blob], file.original_name, { type: file.mime_type })
  4. Create AttachedFile using existing createAttachedFile utility
  ```
- Pass the attachment as third argument to `appendUserMessage`
- Keep the text message: "Tell me about this image: {original_name}"
- Add try/catch: if fetch fails, fall back to text-only message with `console.warn`

**Step C2**: Verify LIM-1
- Upload image in OCR tab, process, click "Open in Chat"
- Confirm image thumbnail appears in attachment tray
- Confirm AI can reference actual image content
- Test error case: delete file from storage, confirm graceful fallback

### Phase D: LIM-3 — CSS Split (pure refactor)

**Step D1**: Create `frontend/src/components/tabs/tools/AudioTranscriber.css`
- Extract lines 294-460 from `ToolsTab.css` (all `.tools-audio__*` rules)
- Preserve exact content — no class name changes

**Step D2**: Add import to `AudioTranscriber.tsx`
- Add `import './AudioTranscriber.css'` to existing imports

**Step D3**: Remove extracted styles from `ToolsTab.css`
- Delete lines 294-460 from `ToolsTab.css`
- Result: `ToolsTab.css` becomes ~293 lines (under 400-line cap)

**Step D4**: Verify LIM-3
- Open Tools tab, navigate to Audio Transcriber
- Visual inspection: all elements render identically
- Run `git diff` — confirm only file moves, no content changes
- Count lines in `ToolsTab.css` — confirm under 400

## Risk Mitigation

### LIM-1: Blob→File for large images
- OCR images are typically under 10MB (compressed JPEG/PNG)
- If fetch fails (file deleted), fall back to text-only message
- No user-facing error — graceful degradation

### LIM-2: Ollama may not always return usage metadata
- `usage` field is optional in SSE contract — frontend checks presence
- Frontend falls back to estimated values with visual indicator
- No breaking change to existing behavior

### LIM-3: No risk
- Pure CSS file split, class names unchanged
- Component already exists and imports can be added trivially

## Verification Checklist

- [ ] LIM-1: OCR image opens in chat with visual attachment
- [ ] LIM-1: AI references actual image content in response
- [ ] LIM-1: Graceful fallback when image fetch fails
- [ ] LIM-2: Real token count displayed (no `~` prefix)
- [ ] LIM-2: Real generation time displayed (not sum of thinking steps)
- [ ] LIM-2: Fallback to estimated values when backend doesn't provide usage
- [ ] LIM-3: `ToolsTab.css` under 400 lines
- [ ] LIM-3: `AudioTranscriber.css` exists with extracted styles
- [ ] LIM-3: No visual regression in Tools tab
- [ ] Constitution: all files under 400 lines
- [ ] Constitution: one concept per file
