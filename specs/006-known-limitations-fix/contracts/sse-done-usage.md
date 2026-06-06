# SSE Done Event Contract Change

**Date**: 2026-06-06
**Affected Endpoint**: `POST /api/chat` (SSE stream)

## Current Contract

```
event: done
data: {"message_id": "uuid", "chat_id": "uuid"}
```

## New Contract (Backward Compatible)

```
event: done
data: {"message_id": "uuid", "chat_id": "uuid", "usage": {"prompt_tokens": 38, "completion_tokens": 142, "total_tokens": 180, "generation_time_ms": 3500}}
```

### Usage object fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt_tokens` | `int` | No | Tokens in the prompt |
| `completion_tokens` | `int` | No | Tokens in the completion |
| `total_tokens` | `int` | No | Sum of prompt + completion |
| `generation_time_ms` | `int` | No | Wall-clock time in ms |

### Backward Compatibility

- The `usage` field is optional — if backend cannot determine metrics (e.g., streaming error, model doesn't report), it is omitted or `null`.
- Existing frontend parsers that only read `message_id` and `chat_id` will continue to work unchanged.
- New frontend code checks `usage` presence before using real values, falling back to estimates.
