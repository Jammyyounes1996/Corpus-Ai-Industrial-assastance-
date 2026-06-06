# API Contracts: Remaining Workspace Tabs

**Date**: 2026-06-06 | **Feature**: [../spec.md](../spec.md)

## Modified Endpoints

### GET /api/chat/{chat_id} — Add retrieved_context to messages

**Change**: Include `retrieved_context` field in each message object.

**Current response** (message object):
```json
{
  "id": 42,
  "chat_id": "uuid",
  "role": "assistant",
  "content": "The hydraulic system...",
  "thinking_steps": "[{\"type\":\"routing\",...}]",
  "created_at": "2026-06-06T10:30:00"
}
```

**Updated response** (message object):
```json
{
  "id": 42,
  "chat_id": "uuid",
  "role": "assistant",
  "content": "The hydraulic system...",
  "thinking_steps": "[{\"type\":\"routing\",...}]",
  "retrieved_context": "[{\"file_id\":\"abc\",\"filename\":\"manual.pdf\",...}]",
  "created_at": "2026-06-06T10:30:00"
}
```

**Notes**: Both `thinking_steps` and `retrieved_context` are JSON-encoded strings (Text column). The frontend must `JSON.parse()` them. Null when no thinking/retrieval occurred.

---

## New Endpoints

### GET /api/files/{file_id}/content

**Purpose**: Serve the raw file content (image, audio, PDF) for browser rendering.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| file_id | string (UUID) | File identifier |

**Response**: `FileResponse` with appropriate `Content-Type` header.

| file_type | Content-Type (examples) |
|-----------|------------------------|
| image | image/jpeg, image/png, image/webp |
| audio | audio/mpeg, audio/wav, audio/ogg |
| pdf | application/pdf |

**Error Responses**:
| Status | Body | Condition |
|--------|------|-----------|
| 404 | `{"error": "NotFound", "message": "File not found: {file_id}"}` | File ID not in database |
| 404 | `{"error": "FileNotFound", "message": "File missing from disk: {file_id}"}` | DB record exists but disk file deleted |

**Headers**: `Content-Disposition: inline; filename="{original_name}"` for browser rendering.

---

### POST /api/evaluate

**Purpose**: Run RAGAS faithfulness + answer_relevancy evaluation on a chat message.

**Request Body**:
```json
{
  "chat_id": "uuid-string",
  "message_id": 42
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| chat_id | string | yes | Chat containing the message |
| message_id | integer | yes | Assistant message to evaluate |

**Success Response** (201 Created):
```json
{
  "id": 1,
  "chat_id": "uuid-string",
  "message_id": 42,
  "faithfulness": 0.85,
  "answer_relevancy": 0.92,
  "model_used": "joe-speedboat/Gemma-4-Uncensored-HauhauCS-Aggressive:e4b",
  "created_at": "2026-06-06T10:35:00"
}
```

**Error Responses**:
| Status | Body | Condition |
|--------|------|-----------|
| 404 | `{"error": "NotFound", "message": "Chat not found"}` | Invalid chat_id |
| 404 | `{"error": "NotFound", "message": "Message not found in chat"}` | message_id not in chat |
| 400 | `{"error": "ValidationError", "message": "Message has no retrieved context"}` | No retrieval data to evaluate |
| 409 | `{"error": "AlreadyExists", "message": "Evaluation already exists for this message"}` | UniqueConstraint violation |
| 500 | `{"error": "EvaluationError", "message": "RAGAS evaluation failed: {details}"}` | Ollama unreachable or model error |

**Notes**:
- Evaluation can take 10-60 seconds depending on context length and Ollama model speed
- Only `faithfulness` and `answer_relevancy` are computed; `context_precision` and `context_recall` are omitted (require ground truth)
- Uses Ollama as the LLM judge via langchain-ollama

---

### GET /api/evaluations

**Purpose**: List evaluation history with optional filtering.

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| chat_id | string | (none) | Filter by chat |
| limit | integer | 50 | Max results (1-100) |
| offset | integer | 0 | Pagination offset |

**Success Response** (200):
```json
{
  "evaluations": [
    {
      "id": 1,
      "chat_id": "uuid-string",
      "message_id": 42,
      "faithfulness": 0.85,
      "answer_relevancy": 0.92,
      "message_preview": "The hydraulic system requires...",
      "created_at": "2026-06-06T10:35:00"
    }
  ],
  "total": 5,
  "limit": 50,
  "offset": 0
}
```

**Notes**: `message_preview` is the first 100 characters of the evaluated assistant message content, joined from the messages table.

---

## Existing Endpoints Used (no changes)

| Endpoint | Used By | Purpose |
|----------|---------|---------|
| GET /api/files | Documents tab, OCR tab | List files with type filter and sort |
| DELETE /api/files/{file_id} | Documents tab | Delete file with confirmation |
| POST /api/ingest/pdf | Documents tab (upload) | Upload PDF |
| POST /api/ingest/audio | Documents tab (upload) | Upload audio |
| POST /api/ingest/image | Documents tab (upload) | Upload image |
| GET /api/chat/{chat_id} | Analysis tab | Get chat with messages (after fix) |
