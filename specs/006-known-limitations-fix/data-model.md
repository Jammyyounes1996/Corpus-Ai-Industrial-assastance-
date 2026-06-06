# Data Model: Phase 5 Known Limitations Fix

**Date**: 2026-06-06

## Entity Changes

### 1. Usage Metadata (NEW — SSE transport only)

Transient data carried in the SSE `done` event. Not persisted to database.

| Field | Type | Description |
|-------|------|-------------|
| `prompt_tokens` | `int` | Number of tokens in the prompt |
| `completion_tokens` | `int` | Number of tokens in the completion |
| `total_tokens` | `int` | Sum of prompt + completion tokens |
| `generation_time_ms` | `int` | Wall-clock generation time in milliseconds |

**Lifecycle**: Created in `answer_node` → propagated via `emit_done` → parsed by frontend → displayed in `AnalysisTab`. Not stored.

### 2. DoneEvent (MODIFIED — frontend type)

Existing entity extended with optional usage field.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message_id` | `string` | Yes | Existing — unchanged |
| `chat_id` | `string` | Yes | Existing — unchanged |
| `usage` | `UsageMetadata or null` | No | **NEW** — real metrics when available |

### 3. AttachedFile (EXISTING — no schema change)

Used as-is. The `file: File` property will receive a File object constructed from the fetched OCR image Blob.

### 4. AudioTranscriber.css (NEW — file entity)

New CSS file containing all `.tools-audio__*` class rules extracted from `ToolsTab.css`. No new CSS classes, no renamed classes. Pure relocation.
