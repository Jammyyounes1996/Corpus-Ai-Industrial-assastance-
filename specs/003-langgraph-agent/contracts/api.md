# API Contracts: LangGraph Agent

**Phase**: 1 | **Date**: 2026-05-22 | **Status**: Complete

## Overview

This document defines the external API contracts for the LangGraph Agent feature, including request/response schemas, error formats, and event types for streaming.

---

## Base URL

```
http://localhost:8000/api
```

---

## Endpoints

### 1. POST /api/chat/stream

Stream agent response with thinking steps via Server-Sent Events (SSE).

**Request Method**: `POST`
**Content-Type**: `application/json`
**Response Type**: `text/event-stream`

#### Request Schema

```json
{
  "chat_id": "550e8400-e29b-41d4-a716-44665544010",
  "message": "What is the recommended maintenance interval for the bearings?",
  "attached_files": ["abc-123-def", "xyz-456-ghi"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `chat_id` | string (UUID) | No | Existing chat ID, or `null` for new conversation |
| `message` | string | Yes | User's question or message (max 10,000 chars) |
| `attached_files` | array[string] | No | File UUIDs to include in context (max 10) |

**Validation Rules**:
- `chat_id` must be valid UUID format if provided
- `message` cannot be empty or whitespace only
- `message` length: 1-10,000 characters
- `attached_files` length: 0-10 items
- All file IDs in `attached_files` must exist in database

#### SSE Event Stream

**Event Types**:

1. **thinking_step** - Agent reasoning progress
2. **token** - Generated answer token
3. **sources** - Source citations
4. **done** - Stream completion

##### Event 1: thinking_step (in_progress)

```
event: thinking_step
data: {"step":"Analyzing your query...","status":"in_progress","node":"router_node","duration_ms":null}
```

##### Event 2: thinking_step (completed)

```
event: thinking_step
data: {"step":"Analyzing your query...","status":"completed","node":"router_node","duration_ms":320}
```

##### Event 3: thinking_step (failed)

```
event: thinking_step
data: {"step":"Searching memory...","status":"failed","node":"qdrant_retrieve_node","duration_ms":1500,"error":"Qdrant connection timeout"}
```

##### Event 4: token

```
event: token
data: {"content":"The"}
```

```
event: token
data: {"content":" recommended"}
```

##### Event 5: sources

```
event: sources
data: {"sources":[{"file_id":"abc-123-def","filename":"pump_manual.pdf","file_type":"pdf","chunk_index":12,"score":0.94,"excerpt":"The bearings should be lubricated every 6 months..."}]}
```

##### Event 6: done

```
event: done
data: {"chat_id":"550e8400-e29b-41d4-a716-44665544010","message_id":42}
```

#### Status Values (thinking_step.status)

| Value | Description |
|-------|-------------|
| `pending` | Step queued, not started |
| `in_progress` | Step currently executing |
| `completed` | Step finished successfully |
| `failed` | Step failed with error |

#### Error Responses

```json
{
  "error": "ValidationError",
  "message": "Message cannot be empty",
  "details": {
    "field": "message",
    "value": ""
  }
}
```

**HTTP Status Codes**:
- `200 OK` - Stream established (SSE response)
- `400 Bad Request` - Validation error
- `404 Not Found` - Chat ID not found (if chat_id provided)
- `500 Internal Server Error` - Server error

---

### 2. GET /api/chats

List all chat sessions.

**Request Method**: `GET`
**Content-Type**: `application/json`

#### Query Parameters (optional)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 50 | Maximum number of chats to return (1-100) |
| `offset` | integer | 0 | Number of chats to skip (pagination) |

#### Response Schema

```json
{
  "chats": [
    {
      "id": "550e8400-e29b-41d4-a716-44665544010",
      "title": "Pump maintenance questions",
      "model_provider": "ollama",
      "model_name": "gemma4:latest",
      "created_at": "2026-05-20T12:34:56.789Z",
      "updated_at": "2026-05-20T14:22:11.234Z",
      "message_count": 8
    },
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "title": "OCR image analysis",
      "model_provider": "ollama",
      "model_name": "gemma4:latest",
      "created_at": "2026-05-19T09:15:00.000Z",
      "updated_at": "2026-05-19T09:30:00.000Z",
      "message_count": 3
    }
  ],
  "total": 2
}
```

| Field | Type | Description |
|-------|------|-------------|
| `chats` | array | List of chat sessions |
| `chats[].id` | string (UUID) | Chat session ID |
| `chats[].title` | string | Auto-generated title |
| `chats[].model_provider` | string | LLM provider used |
| `chats[].model_name` | string | Specific model name |
| `chats[].created_at` | string (ISO8601) | Creation timestamp |
| `chats[].updated_at` | string (ISO8601) | Last activity timestamp |
| `chats[].message_count` | integer | Number of messages in chat |
| `total` | integer | Total number of chats (for pagination) |

#### Error Responses

```json
{
  "error": "ValidationError",
  "message": "Limit must be between 1 and 100",
  "details": {
    "field": "limit",
    "value": 200
  }
}
```

**HTTP Status Codes**:
- `200 OK` - Success
- `400 Bad Request` - Invalid query parameters
- `500 Internal Server Error` - Server error

---

### 3. GET /api/chat/{chat_id}

Get full chat with all messages.

**Request Method**: `GET`
**Content-Type**: `application/json`

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | string (UUID) | Yes | Chat session ID |

#### Response Schema

```json
{
  "chat": {
    "id": "550e8400-e29b-41d4-a716-44665544010",
    "title": "Pump maintenance questions",
    "model_provider": "ollama",
    "model_name": "gemma4:latest",
    "created_at": "2026-05-20T12:34:56.789Z",
    "updated_at": "2026-05-20T14:22:11.234Z",
    "messages": [
      {
        "id": 1,
        "role": "user",
        "content": "What is the recommended maintenance interval for the bearings?",
        "thinking_steps": [],
        "retrieved_context": [],
        "attached_files": [],
        "created_at": "2026-05-20T12:34:56.789Z"
      },
      {
        "id": 2,
        "role": "assistant",
        "content": "Based on the pump manual, the recommended maintenance interval for bearings is every 6 months. This includes lubrication and visual inspection for wear indicators.",
        "thinking_steps": [
          {
            "step": "Analyzing your query...",
            "status": "completed",
            "node": "router_node",
            "duration_ms": 320
          },
          {
            "step": "Reading PDF documents...",
            "status": "completed",
            "node": "groundx_retrieve_node",
            "duration_ms": 2450
          },
          {
            "step": "Searching memory (RAG)...",
            "status": "completed",
            "node": "qdrant_retrieve_node",
            "duration_ms": 890
          },
          {
            "step": "Analyzing information...",
            "status": "completed",
            "node": "context_synthesis_node",
            "duration_ms": 210
          },
          {
            "step": "Generating answer...",
            "status": "completed",
            "node": "answer_node",
            "duration_ms": 3400
          }
        ],
        "retrieved_context": [
          {
            "file_id": "abc-123-def",
            "filename": "pump_manual.pdf",
            "file_type": "pdf",
            "chunk_index": 12,
            "score": 0.94,
            "excerpt": "The bearings should be lubricated every 6 months..."
          }
        ],
        "attached_files": [],
        "created_at": "2026-05-20T12:35:02.123Z"
      }
    ]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `chat` | object | Chat session details |
| `chat.messages` | array | All messages in chronological order |
| `chat.messages[].id` | integer | Message ID |
| `chat.messages[].role` | string | Message role (user/assistant) |
| `chat.messages[].content` | string | Message content |
| `chat.messages[].thinking_steps` | array | ThinkingStep objects (for assistant messages) |
| `chat.messages[].retrieved_context` | array | Source citations (for assistant messages) |
| `chat.messages[].attached_files` | array | File UUIDs (for user messages) |
| `chat.messages[].created_at` | string (ISO8601) | Message timestamp |

#### Error Responses

```json
{
  "error": "NotFoundError",
  "message": "Chat not found: 550e8400-e29b-41d4-a716-44665544010",
  "details": {
    "chat_id": "550e8400-e29b-41d4-a716-44665544010"
  }
}
```

**HTTP Status Codes**:
- `200 OK` - Success
- `404 Not Found` - Chat ID not found
- `500 Internal Server Error` - Server error

---

### 4. DELETE /api/chat/{chat_id}

Delete a chat session and all associated messages.

**Request Method**: `DELETE`
**Content-Type**: `application/json`

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | string (UUID) | Yes | Chat session ID |

#### Response

**Status Code**: `204 No Content`
**Body**: Empty

#### Error Responses

```json
{
  "error": "NotFoundError",
  "message": "Chat not found: 550e8400-e29b-41d4-a716-44665544010",
  "details": {
    "chat_id": "550e8400-e29b-41d4-a716-44665544010"
  }
}
```

**HTTP Status Codes**:
- `204 No Content` - Successfully deleted
- `404 Not Found` - Chat ID not found
- `500 Internal Server Error` - Server error

---

## Error Response Schema (Common)

All error responses follow this format:

```json
{
  "error": "ErrorType",
  "message": "Human-readable error description",
  "details": {
    "field": "optional_field_name",
    "value": "provided_value"
  }
}
```

### Error Types

| Error Type | HTTP Status | When Used |
|------------|-------------|-----------|
| `ValidationError` | 400 | Input validation failed |
| `NotFoundError` | 404 | Resource not found |
| `AgentError` | 500 | Agent execution failed |
| `RetrievalError` | 500 | Retrieval service failed |
| `InternalServerError` | 500 | Unexpected server error |

---

## CORS Configuration

```
Allowed Origins: http://localhost:8501
Allowed Methods: GET, POST, DELETE, OPTIONS
Allowed Headers: Content-Type, Authorization
Max Age: 86400
```

---

## Rate Limiting

No rate limiting for single-user mode.

---

**Status**: API contracts complete, validated against spec requirements. Ready for implementation.