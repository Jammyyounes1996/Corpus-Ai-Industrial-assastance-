# Research: Phase 5 Known Limitations Fix

**Date**: 2026-06-06
**Spec**: [spec.md](./spec.md)

## LIM-1: OCR Image Attachment

### Decision: Fetch image Blob → convert to File → attach to message

**Rationale**: The backend chat endpoint already accepts `attached_files: list[str]` (file IDs) in the `StreamRequest` schema (`backend/schemas/chat.py`). The frontend `appendUserMessage` already accepts `attachments?: AttachedFile[]`. The `AttachedFile` type requires a `file: File` browser object. Since OCR images are already uploaded files with backend IDs, we fetch the binary via `GET /api/files/{file_id}/content`, convert the response Blob to a File object using `new File([blob], filename, { type })`, and pass it as an attachment.

**Alternatives considered**:
1. **Pass file_id string directly** — Backend already resolves file_ids via `crud.get_files_by_ids()`. However, the frontend `AttachedFile` type requires a real `File` object for the thumbnail preview in `AttachmentTray`. Without it, no visual attachment shown.
2. **Reuse existing upload flow** — Would re-upload an already-uploaded file. Wasteful and incorrect.

### Risk: Large image Blob→File conversion

**Mitigation**: OCR images are typically compressed (JPEG/PNG, under 10MB). The Blob→File conversion is a memory operation with no disk I/O. If the fetch fails (file deleted), catch the error and fall back to text-only message with a console warning.

## LIM-2: Real Token Count and Generation Time

### Decision: Propagate Ollama usage metadata through SSE `done` event

**Rationale**: The Ollama `/api/generate` endpoint returns `eval_count` (completion tokens), `prompt_eval_count` (prompt tokens), and `total_duration` (nanoseconds) in its final response. The backend `answer_node` (`backend/agent/nodes/answer.py`) already tracks `start_time` and collects tokens, but discards this data after logging. The fix is: (1) capture Ollama's usage stats in `answer_node`, (2) propagate through `emit_done` in `streaming.py`, (3) parse in frontend `validateDoneEvent`, (4) display in `AnalysisTab`.

**Backend changes needed**:
- `streaming.py`: Add optional `usage` dict to `emit_done` signature
- `answer_node`: Capture Ollama response metadata, compute duration, pass to `emit_done`
- The `OllamaClient.generate_stream` may need to yield a final metadata chunk

**Frontend changes needed**:
- `chat.ts` (`DoneEvent` type): Add optional `usage` field with `prompt_tokens`, `completion_tokens`, `total_tokens`, `generation_time_ms`
- `chatStreamParser.ts` (`validateDoneEvent`): Extract optional `usage` from done data
- `AnalysisTab.tsx`: Replace estimated values with real values when available

**Alternatives considered**:
1. **New SSE event type** — Would require parsing a new event in the stream parser. Using `done` is simpler since it's the terminal event.
2. **Polling endpoint** — Additional HTTP request per message. Unnecessary complexity.

### Ollama API response format (reference)

```json
{
  "eval_count": 142,
  "prompt_eval_count": 38,
  "total_duration": 3500000000
}
```

`total_duration` is in nanoseconds. Convert: `duration_ms = total_duration / 1_000_000`.

## LIM-3: CSS File Split

### Decision: Extract audio transcriber styles to `AudioTranscriber.css`

**Rationale**: Audio transcriber styles (lines 294-460, 167 lines) are the largest cohesive block and `AudioTranscriber.tsx` is already a separate component. This brings `ToolsTab.css` from 460 → 293 lines (well under 400-line constitution cap). The `.tools-audio__*` class names are BEM-ish (matching constitution §10.2) and are only used in `AudioTranscriber.tsx`.

**Alternatives considered**:
1. **Extract gauge card styles** — Only ~60 lines. ToolsTab.css would be 400 lines (barely under limit). Less impactful.
2. **Extract both** — Over-engineering for this fix. One extraction is sufficient.

### No risk

Pure file move. Class names unchanged. No behavior change.
