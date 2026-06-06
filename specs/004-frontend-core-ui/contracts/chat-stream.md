# Contract: Chat Stream

## Contract status

Mismatch confirmed: the backend does not expose `POST /api/chat/stream`. The real backend-compatible stream endpoint is `POST /api/chat/{chat_id}/stream` and it requires an existing chat UUID.

## Endpoint path

`/api/chat/{chat_id}/stream`

## HTTP method

`POST`

## Prerequisite chat route

Create a chat before streaming:

- Endpoint: `/api/chats`
- Method: `POST`
- Body: `{ "title"?: string, "model_provider"?: string, "model_name"?: string }`
- Response fields: `id`, `title`, `model_provider`, `model_name`, `created_at`, `updated_at`

## Headers

- Request: `Content-Type: application/json`
- Request: `Accept: text/event-stream`
- Response: SSE response produced by `EventSourceResponse`
- CORS currently allows origin `http://localhost:8501`, methods `GET`, `POST`, `DELETE`, `OPTIONS`, and headers `Content-Type`, `Authorization`.

## Request body schema

```json
{
  "query": "string, required, min length 1, max length from MAX_MESSAGE_LENGTH",
  "model_provider": "string, optional, defaults to DEFAULT_MODEL_PROVIDER",
  "model_name": "string, optional, defaults to DEFAULT_MODEL_NAME",
  "attached_files": ["string file_id", "..."]
}
```

Notes:

- `attached_files` is optional and truncated by backend validation to `MAX_ATTACHED_FILES`.
- The route currently uses the persisted chat `model_provider` and `model_name` in agent state; request model fields are validated but not used to override the chat model in the route.
- If any `attached_files` ID is missing from the database, the route returns `404` before starting the stream.

## Example request body

```json
{
  "query": "Summarize the startup procedure risks.",
  "model_provider": "ollama",
  "model_name": "joe-speedboat/Gemma-4-Uncensored-HauhauCS-Aggressive:e4b",
  "attached_files": ["4f8d0d9e-7d3d-4d58-9f90-5c14e7e2a001"]
}
```

## Stream response format

The backend returns Server-Sent Events. Each yielded item has an SSE event name and JSON-encoded data payload.

Wire format:

```text
event: <event_name>
data: {"field":"value"}

```

## Frame delimiter rules

- SSE frames are delimited by a blank line (`\n\n`).
- A frame may contain an `event:` line and one or more `data:` lines.
- Frontend parsing must buffer partial chunks until a full SSE frame delimiter is received.
- Do not parse this stream as NDJSON.

## Event types

- `thinking_step`
- `token`
- `sources`
- `done`
- `error`

## Event payload schemas

### `thinking_step`

```json
{
  "type": "string",
  "content": "string",
  "metadata": {},
  "timestamp": "ISO-8601 string"
}
```

### `token`

```json
{
  "token": "string"
}
```

### `sources`

```json
{
  "sources": [
    {
      "file_id": "string",
      "filename": "string",
      "file_type": "string",
      "chunk_index": 0,
      "score": 0.0,
      "excerpt": "string"
    }
  ],
  "total_count": 1,
  "has_more": false,
  "hidden_count": 0
}
```

### `done`

```json
{
  "message_id": "string",
  "chat_id": "string"
}
```

### `error`

```json
{
  "error": "string"
}
```

## Example event sequence

```text
event: thinking_step
data: {"type":"retrieval","content":"Searching relevant documents","metadata":{},"timestamp":"2026-05-31T10:00:00+00:00"}

event: token
data: {"token":"The"}

event: token
data: {"token":" procedure"}

event: sources
data: {"sources":[{"file_id":"file-1","filename":"manual.pdf","file_type":"pdf","chunk_index":0,"score":0.87,"excerpt":"Start-up procedure..."}],"total_count":1,"has_more":false,"hidden_count":0}

event: done
data: {"message_id":"123","chat_id":"4f8d0d9e-7d3d-4d58-9f90-5c14e7e2a001"}

```

## Error event shape

Mid-stream errors use:

```json
{
  "error": "An internal error occurred. Please try again."
}
```

Pre-stream validation errors are normal HTTP errors:

- `400` for invalid `chat_id`.
- `404` for missing chat.
- `404` for missing attached file IDs.

## Mid-stream failure behavior

- Backend catches stream exceptions, cancels the graph task if needed, persists any collected assistant text, emits an `error` event, and then emits `done` from the `finally` block if `done` was not already sent.
- Frontend must treat an `error` event as a failed assistant response even if a `done` event follows.
- Frontend must keep any partial streamed text visible with an error state.

## Retry rules

- Do not auto-retry a stream after tokens have started because the backend persists user and assistant messages before streaming.
- For pre-stream network/HTTP failures, allow user-triggered retry only.
- On `404` missing attachments, require re-upload or removal of invalid attachment references before retry.

## Abort behavior

- Frontend should use `AbortController` for user cancellation and navigation cleanup.
- Aborting the request may leave a partial assistant message persisted by the backend.
- UI should mark the local message as stopped/cancelled and avoid assuming backend rollback.

## Attachment reference handling

- `attached_files` must contain backend file IDs only.
- File IDs come from successful ingestion responses as `file_id`.
- Do not send raw filenames, local paths, browser `File` objects, or unpersisted temporary IDs to the stream endpoint.
