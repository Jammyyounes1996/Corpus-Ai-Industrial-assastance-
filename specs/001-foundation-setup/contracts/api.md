# API Contract: Industrial AI Assistant

**Feature**: 001-foundation-setup
**Date**: 2026-05-18
**Version**: 1.0

---

## Base URL

```
http://localhost:8000
```

All endpoints are prefixed with `/api/`.

---

## CORS Configuration

**Allowed Origins**: `http://localhost:8501` (Streamlit default)
**Allowed Methods**: GET, POST, PUT, DELETE
**Allowed Headers**: `*`
**Allow Credentials**: `true`

---

## Common Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (successful delete) |
| 400 | Bad Request (validation error) |
| 404 | Not Found |
| 422 | Unprocessable Entity (Pydantic validation) |
| 500 | Internal Server Error |

---

## Endpoints

### 1. Health Check

**Endpoint**: `GET /health`

**Purpose**: Verify backend is operational.

**Request**:
```
GET /health
```

**Response**:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "database": "connected",
  "qdrant": "connected",
  "ollama": "connected"
}
```

**Phase**: 1 (Foundation)

---

### 2. Settings

#### GET /api/settings

**Purpose**: Retrieve current application settings.

**Response**:
```json
{
  "model_provider": "ollama",
  "model_name": "gemma2:latest",
  "theme": "light",
  "gemini_api_key_masked": null,
  "grok_api_key_masked": null
}
```

**Phase**: 6 (Advanced Features)

---

#### PUT /api/settings

**Purpose**: Update application settings.

**Request Body**:
```json
{
  "model_provider": "ollama",
  "model_name": "gemma2:latest",
  "theme": "light",
  "gemini_api_key": null,
  "grok_api_key": null
}
```

**Response**: 200 OK

**Phase**: 6 (Advanced Features)

---

#### POST /api/settings/test-connection

**Purpose**: Test connection to selected model provider.

**Request Body**:
```json
{
  "provider": "ollama",
  "model": "gemma2:latest",
  "api_key": null
}
```

**Response**:
```json
{
  "status": "connected",
  "details": {
    "model": "gemma2:latest",
    "latency_ms": 124
  }
}
```

**Phase**: 6 (Advanced Features)

---

### 3. Files

#### GET /api/files

**Purpose**: List all uploaded files.

**Query Parameters**:
- `type`: Optional filter by file type (pdf, audio, image)
- `status`: Optional filter by indexing status
- `limit`: Optional limit (default 100)

**Response**:
```json
{
  "files": [
    {
      "id": "uuid-v4",
      "original_name": "manual.pdf",
      "file_type": "pdf",
      "size_bytes": 1048576,
      "indexing_status": "indexed",
      "created_at": "2026-05-18T10:00:00Z"
    }
  ]
}
```

**Phase**: 5 (Remaining Tabs)

---

#### DELETE /api/files/{file_id}

**Purpose**: Delete a file and all associated data.

**Response**: 204 No Content

**Phase**: 5 (Remaining Tabs)

---

#### GET /api/files/{file_id}/download

**Purpose**: Download an uploaded file.

**Response**: File content with appropriate Content-Type header.

**Phase**: 5 (Remaining Tabs)

---

### 4. Chats

#### GET /api/chats

**Purpose**: List all chats.

**Query Parameters**:
- `project_id`: Optional filter by project ID
- `limit`: Optional limit (default 50)

**Response**:
```json
{
  "chats": [
    {
      "id": "uuid-v4",
      "title": "Pump maintenance query",
      "project_id": null,
      "model_name": "gemma2:latest",
      "created_at": "2026-05-18T10:00:00Z",
      "updated_at": "2026-05-18T10:05:00Z"
    }
  ]
}
```

**Phase**: 3 (LangGraph Agent)

---

#### GET /api/chat/{chat_id}

**Purpose**: Retrieve a single chat with all messages.

**Response**:
```json
{
  "id": "uuid-v4",
  "title": "Pump maintenance query",
  "project_id": null,
  "model_name": "gemma2:latest",
  "created_at": "2026-05-18T10:00:00Z",
  "updated_at": "2026-05-18T10:05:00Z",
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "What is the maintenance interval?",
      "attached_files": [],
      "created_at": "2026-05-18T10:00:00Z"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "According to the manual...",
      "thinking_steps": [...],
      "retrieved_context": [...],
      "attached_files": ["uuid-v4"],
      "created_at": "2026-05-18T10:00:05Z"
    }
  ]
}
```

**Phase**: 3 (LangGraph Agent)

---

#### DELETE /api/chat/{chat_id}

**Purpose**: Delete a chat and all its messages.

**Response**: 204 No Content

**Phase**: 3 (LangGraph Agent)

---

#### POST /api/chat/stream

**Purpose**: Send a message and stream the agent's response via SSE.

**Request Body**:
```json
{
  "chat_id": null,
  "message": "What is the maintenance interval?",
  "attached_files": ["uuid-v4"]
}
```

**Response**: Server-Sent Events stream

**Event Types**:

1. **thinking_step** - Agent step status update
   ```
   event: thinking_step
   data: {"step": "Reading PDF documents...", "status": "in_progress", "node": "groundx_retrieve"}
   ```
   ```
   event: thinking_step
   data: {"step": "Reading PDF documents...", "status": "completed", "node": "groundx_retrieve", "duration_ms": 1240}
   ```

2. **token** - Streaming response token
   ```
   event: token
   data: {"content": "The main"}
   ```

3. **sources** - Retrieved sources (sent once, after retrieval)
   ```
   event: sources
   data: {"sources": [{"file_id": "...", "filename": "manual.pdf", "chunk": "...", "score": 0.92}]}
   ```

4. **done** - Stream complete
   ```
   event: done
   data: {"chat_id": "uuid-v4", "message_id": 42}
   ```

**Phase**: 3 (LangGraph Agent)

---

### 5. Ingestion

#### POST /api/ingest/pdf

**Purpose**: Upload and index a PDF file.

**Request**: `multipart/form-data` with `file` field.

**Response**:
```json
{
  "file_id": "uuid-v4",
  "filename": "manual.pdf",
  "status": "processing",
  "groundx_id": "doc-12345"
}
```

**Phase**: 2 (Ingestion Pipeline)

---

#### POST /api/ingest/audio

**Purpose**: Upload and transcribe an audio file.

**Request**: `multipart/form-data` with `file` field.

**Response**:
```json
{
  "file_id": "uuid-v4",
  "filename": "recording.mp3",
  "status": "indexed",
  "duration_seconds": 324.5,
  "language": "en"
}
```

**Phase**: 2 (Ingestion Pipeline)

---

#### POST /api/ingest/image

**Purpose**: Upload and OCR an image file.

**Request**: `multipart/form-data` with `file` field.

**Response**:
```json
{
  "file_id": "uuid-v4",
  "filename": "nameplate.jpg",
  "status": "indexed",
  "extracted_text": "MODEL: XJ-2000..."
}
```

**Phase**: 2 (Ingestion Pipeline)

---

### 6. OCR

#### GET /api/ocr/history

**Purpose**: Retrieve all OCR'd images.

**Response**:
```json
{
  "images": [
    {
      "id": 42,
      "file_id": "uuid-v4",
      "extracted_text": "MODEL: XJ-2000...",
      "model_used": "gemma2:9b-vision",
      "filename": "nameplate.jpg",
      "created_at": "2026-05-18T10:00:00Z"
    }
  ]
}
```

**Phase**: 5 (Remaining Tabs)

---

#### GET /api/ocr/{file_id}

**Purpose**: Retrieve OCR result for a specific image.

**Response**:
```json
{
  "id": 42,
  "file_id": "uuid-v4",
  "extracted_text": "MODEL: XJ-2000...",
  "model_used": "gemma2:9b-vision",
  "filename": "nameplate.jpg",
  "created_at": "2026-05-18T10:00:00Z"
}
```

**Phase**: 5 (Remaining Tabs)

---

### 7. Evaluation

#### POST /api/evaluate

**Purpose**: Run RAGAS evaluation on a chat message.

**Request Body**:
```json
{
  "chat_id": "uuid-v4",
  "message_id": 42
}
```

**Response**: Server-Sent Events stream with progress events.

**Event Types**:

1. **eval_progress** - Evaluation progress
   ```
   event: eval_progress
   data: {"metric": "faithfulness", "status": "calculating"}
   ```

2. **eval_result** - Final results
   ```
   event: eval_result
   data: {
     "faithfulness": 0.92,
     "answer_relevancy": 0.88,
     "context_precision": 0.95,
     "context_recall": 0.87
   }
   ```

3. **done** - Stream complete
   ```
   event: done
   data: {}
   ```

**Phase**: 5 (Remaining Tabs)

---

#### GET /api/evaluations

**Purpose**: List all evaluation results.

**Response**:
```json
{
  "evaluations": [
    {
      "id": 1,
      "chat_id": "uuid-v4",
      "message_id": 42,
      "faithfulness": 0.92,
      "answer_relevancy": 0.88,
      "context_precision": 0.95,
      "context_recall": 0.87,
      "created_at": "2026-05-18T10:00:00Z"
    }
  ]
}
```

**Phase**: 5 (Remaining Tabs)

---

### 8. Projects

#### GET /api/projects

**Purpose**: List all projects.

**Response**:
```json
{
  "projects": [
    {
      "id": 1,
      "name": "Pump Maintenance",
      "created_at": "2026-05-18T10:00:00Z",
      "chat_count": 5
    }
  ]
}
```

**Phase**: 6 (Advanced Features)

---

#### POST /api/projects

**Purpose**: Create a new project.

**Request Body**:
```json
{
  "name": "Pump Maintenance"
}
```

**Response**:
```json
{
  "id": 1,
  "name": "Pump Maintenance",
  "created_at": "2026-05-18T10:00:00Z"
}
```

**Phase**: 6 (Advanced Features)

---

#### PUT /api/projects/{id}

**Purpose**: Update a project name.

**Request Body**:
```json
{
  "name": "New Name"
}
```

**Response**: 200 OK

**Phase**: 6 (Advanced Features)

---

#### DELETE /api/projects/{id}

**Purpose**: Delete a project (chats move to "unsorted").

**Response**: 204 No Content

**Phase**: 6 (Advanced Features)

---

#### POST /api/projects/{id}/chats

**Purpose**: Move chats to a project.

**Request Body**:
```json
{
  "chat_ids": ["uuid-v4", "uuid-v5"]
}
```

**Response**: 200 OK

**Phase**: 6 (Advanced Features)

---

## Error Response Format

All error responses follow this format:

```json
{
  "error": "ErrorType",
  "message": "Human-readable error message",
  "details": {
    "field": "validation_error_details",
    "id": "related_entity_id"
  }
}
```

**Common Error Types**:
- `ValidationError` - Pydantic validation failure
- `NotFoundError` - Entity does not exist
- `IngestionError` - File processing failure
- `RetrievalError` - Vector search failure
- `AgentError` - LangGraph execution failure
- `OllamaConnectionError` - Ollama unreachable
- `QdrantConnectionError` - Qdrant unreachable

---

## Rate Limiting

Phase 1-7: No rate limiting (local desktop application).

Future: Consider token bucket for API endpoints if public deployment is needed.

---

## Versioning

API version tracked via response headers:
```
X-API-Version: 1.0
```

Breaking changes will increment major version.

---

**End of API Contract**