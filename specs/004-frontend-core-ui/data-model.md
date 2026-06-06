# Data Model: Frontend Core UI

This model defines frontend-only entities for Phase 4. It is aligned to the verified contracts in `contracts/chat-stream.md`, `contracts/file-upload.md`, and `contracts/status.md`.

## Entity: ChatSession

**Purpose**:
Represents one local conversation in the React sidebar and Chat workspace while also tracking the backend chat UUID required by `POST /api/chat/{chat_id}/stream`.

**Fields**:

| Field | Type | Required | Description |
|---|---|---:|---|
| `id` | `string` | Yes | Local frontend session ID used for React keys and local state. |
| `backendChatId` | `string \| null` | No | Backend chat UUID returned by `POST /api/chats`; required before streaming. |
| `title` | `string` | Yes | Sidebar display title; defaults to `New chat` until first user message or backend title exists. |
| `messages` | `Message[]` | Yes | Ordered local messages for this session. |
| `createdAt` | `string` | Yes | ISO timestamp for local session creation. |
| `updatedAt` | `string` | Yes | ISO timestamp used for sorting and relative timestamp display. |
| `status` | `'empty' \| 'creating_remote' \| 'ready' \| 'failed'` | Yes | Local lifecycle for chat creation and use. |
| `modelProvider` | `string \| 'Unknown'` | Yes | Real provider from backend chat response when available; otherwise `Unknown`. |
| `modelName` | `string \| 'Unknown'` | Yes | Real model name from backend chat response when available; otherwise `Unknown`. |

**Validation Rules**:
- `id` must be non-empty and unique within local state.
- `backendChatId` must be a non-empty UUID-like string before opening the stream endpoint.
- `title` must be non-empty after trimming; display components may truncate it visually.
- `messages` must preserve insertion order.
- `createdAt` and `updatedAt` must be valid ISO timestamp strings.
- `modelProvider` and `modelName` must not use fake values; use `Unknown` when the backend has not provided real values.

**Relationships**:
- Owns many `Message` entities.
- Provides `backendChatId` to `StreamEvent` handling through the chat stream service.
- Supplies optional real model/provider display values to `ConnectionStatus` when selected.

**State Transitions**:
- `empty -> creating_remote` when the user sends the first message and no backend chat exists.
- `creating_remote -> ready` when `POST /api/chats` returns `id`.
- `creating_remote -> failed` when backend chat creation fails.
- `ready -> ready` when messages or stream updates change `updatedAt`.

## Entity: Message

**Purpose**:
Represents one local user or assistant message rendered in the Chat workspace.

**Fields**:

| Field | Type | Required | Description |
|---|---|---:|---|
| `id` | `string` | Yes | Local message ID used for rendering and updates. |
| `sessionId` | `string` | Yes | Owning `ChatSession.id`. |
| `backendMessageId` | `string \| null` | No | Backend `message_id` from the stream `done` event when available. |
| `role` | `'user' \| 'assistant'` | Yes | Message author. |
| `content` | `string` | Yes | User text or assistant markdown buffer. |
| `createdAt` | `string` | Yes | ISO timestamp for display. |
| `status` | `'draft' \| 'uploading' \| 'streaming' \| 'complete' \| 'failed' \| 'cancelled'` | Yes | Local message lifecycle. |
| `attachments` | `UploadedAttachmentReference[]` | Yes | Uploaded backend file references shown on user messages. Empty for assistant messages. |
| `thinkingSteps` | `ThinkingStep[]` | Yes | Assistant processing steps. Empty for user messages. |
| `sources` | `SourceReference[]` | Yes | Assistant source citations. Empty until a `sources` stream event arrives. |
| `error` | `FrontendError \| null` | No | Friendly frontend error for failed or cancelled states. |

**Validation Rules**:
- `id`, `sessionId`, `role`, `content`, `createdAt`, and `status` are required.
- User messages must have non-empty trimmed `content` before send; attachment-only send is out of scope.
- Assistant messages may have empty `content` while `status` is `streaming`.
- `attachments` are allowed only on user messages in Phase 4.
- `thinkingSteps` and `sources` are allowed only on assistant messages.
- `backendMessageId` may be set only from a real backend `done.message_id` value.

**Relationships**:
- Belongs to one `ChatSession`.
- User messages may reference many `UploadedAttachmentReference` entities.
- Assistant messages may contain many `ThinkingStep` and `SourceReference` entities.
- Failed messages reference one `FrontendError`.

**State Transitions**:
- User: `draft -> uploading -> complete` when selected files must upload first.
- User: `draft -> complete` when no files are selected.
- User: `uploading -> failed` when upload fails and stream is not opened.
- Assistant: `streaming -> complete` when a `done` event arrives without a prior `error` event.
- Assistant: `streaming -> failed` when a stream `error`, parse failure, HTTP failure, or network drop occurs.
- Assistant: `streaming -> cancelled` when the user aborts the request.

## Entity: ThinkingStep

**Purpose**:
Displays one backend `thinking_step` SSE event in the Thinking card.

**Fields**:

| Field | Type | Required | Description |
|---|---|---:|---|
| `id` | `string` | Yes | Stable local ID, derived from backend `type` and `timestamp` when available. |
| `type` | `string` | Yes | Backend event `type`, such as retrieval or generation. |
| `content` | `string` | Yes | Backend event `content` shown to the user. |
| `metadata` | `Record<string, unknown>` | Yes | Backend event `metadata`; empty object when omitted. |
| `timestamp` | `string` | Yes | Backend ISO timestamp from the event. |
| `status` | `'received' \| 'complete' \| 'failed'` | Yes | UI display state for the step. |

**Validation Rules**:
- `type`, `content`, and `timestamp` must be non-empty strings.
- `metadata` must be an object; invalid metadata maps to an empty object and a parse error is recorded separately.
- `timestamp` must be parseable enough for ordering; if not, preserve event arrival order.
- `status` is frontend-derived and must not imply backend success after a stream `error` event.

**Relationships**:
- Belongs to one assistant `Message`.
- Is created from one `StreamEvent` with `eventName: 'thinking_step'`.

**State Transitions**:
- `received -> complete` when the stream completes successfully.
- `received -> failed` when an `error` event or stream failure occurs before successful completion.

## Entity: SourceReference

**Purpose**:
Represents one backend source citation from a `sources` SSE event and renders as a source chip below an assistant response.

**Fields**:

| Field | Type | Required | Description |
|---|---|---:|---|
| `file_id` | `string` | Yes | Backend file ID for the cited file. |
| `filename` | `string` | Yes | Backend filename for display. |
| `file_type` | `string` | Yes | Backend file type string used to choose a UI icon. |
| `chunk_index` | `number` | Yes | Backend chunk index cited by the answer. |
| `score` | `number` | Yes | Backend relevance score. |
| `excerpt` | `string` | Yes | Backend excerpt shown in tooltip or expanded text when used. |

**Validation Rules**:
- `file_id` and `filename` must be non-empty strings.
- `chunk_index` must be an integer greater than or equal to 0.
- `score` must be a finite number; do not assume a normalized range unless backend guarantees it.
- Unknown `file_type` values must render with a generic source icon instead of throwing.

**Relationships**:
- Belongs to one assistant `Message`.
- Is created from one item in a `sources` `StreamEvent` payload.
- `SourceChips` shows the first 3 and summarizes the remainder using backend `hidden_count` or a local count.

**State Transitions**:
- `absent -> available` when a `sources` event arrives.
- `available -> replaced` when a later `sources` event for the same assistant message arrives.

## Entity: AttachedFile

**Purpose**:
Tracks a browser-selected file before and during upload, including preview data and validation state.

**Fields**:

| Field | Type | Required | Description |
|---|---|---:|---|
| `id` | `string` | Yes | Local attachment ID. |
| `file` | `File` | Yes | Browser `File` object; never sent in the chat stream body. |
| `filename` | `string` | Yes | `File.name` for display. |
| `mimeType` | `string` | Yes | `File.type` used to choose `/api/ingest/pdf`, `/api/ingest/audio`, or `/api/ingest/image`. |
| `kind` | `'pdf' \| 'audio' \| 'image' \| 'unsupported'` | Yes | Frontend category derived from MIME type. |
| `sizeBytes` | `number` | Yes | `File.size`. |
| `previewUrl` | `string \| null` | No | Object URL for image thumbnails only. |
| `status` | `'selected' \| 'invalid' \| 'uploading' \| 'uploaded' \| 'failed' \| 'removed'` | Yes | Local upload lifecycle. |
| `uploadedReference` | `UploadedAttachmentReference \| null` | No | Backend file reference after successful upload. |
| `error` | `FrontendError \| null` | No | Validation or upload error. |

**Validation Rules**:
- `filename`, `mimeType`, `kind`, `sizeBytes`, and `status` are required.
- Supported MIME types must match `contracts/file-upload.md` exactly.
- `sizeBytes` must be greater than 0 and within the known size limit for the selected kind when client-side validation can determine it.
- `uploadedReference` must exist before the attachment can contribute a file ID to `attached_files`.
- `previewUrl` must be revoked when the file is removed, uploaded and cleared, or the component unmounts.

**Relationships**:
- Belongs to the input/attachment hook while pending.
- Produces one `UploadedAttachmentReference` after a successful upload.
- May be copied into a user `Message` only as the uploaded reference, not as a browser `File`.

**State Transitions**:
- `selected -> invalid` when type, size, or count validation fails.
- `selected -> uploading` when Send starts.
- `uploading -> uploaded` when the ingestion endpoint returns `file_id`.
- `uploading -> failed` when upload returns an error or network failure.
- `selected -> removed` or `failed -> removed` when the user removes the file.

## Entity: UploadedAttachmentReference

**Purpose**:
Stores the successful backend ingestion response that can be shown on the user message and passed to chat streaming as a file ID.

**Fields**:

| Field | Type | Required | Description |
|---|---|---:|---|
| `file_id` | `string` | Yes | Backend file ID returned by the upload endpoint. |
| `filename` | `string` | Yes | Backend filename. |
| `status` | `'processing' \| 'indexed' \| string` | Yes | Backend ingestion status; PDF may legitimately be `processing`. |
| `size_bytes` | `number` | Yes | Backend file size in bytes. |
| `kind` | `'pdf' \| 'audio' \| 'image'` | Yes | Endpoint category used for upload. |
| `duration_seconds` | `number \| null` | No | Optional audio-specific backend field. |
| `language` | `string \| null` | No | Optional audio-specific backend field. |
| `extracted_text` | `string \| null` | No | Optional image-specific backend field. |

**Validation Rules**:
- `file_id`, `filename`, `status`, `size_bytes`, and `kind` are required after upload success.
- `file_id` must be the only attachment value sent in chat stream `attached_files`.
- `size_bytes` must be greater than or equal to 0.
- `processing` must be displayed as a real backend state, not converted to fake completion.

**Relationships**:
- Created from one successful upload response.
- Referenced by a user `Message`.
- Supplies the string values for `StreamEvent` request body field `attached_files`.

**State Transitions**:
- `created -> referenced_in_message` when the user message is appended locally.
- `referenced_in_message -> sent_to_stream` when its `file_id` is included in the stream request body.

## Entity: ConnectionStatus

**Purpose**:
Represents the real `/health` status and safe UI fallbacks for fields that the backend does not expose.

**Fields**:

| Field | Type | Required | Description |
|---|---|---:|---|
| `state` | `'loading' \| 'connected' \| 'degraded' \| 'disconnected'` | Yes | Top-level frontend status derived from request result and `/health.status`. |
| `status` | `'ok' \| 'degraded' \| 'Unavailable'` | Yes | Raw `/health.status` when available, otherwise `Unavailable`. |
| `version` | `string \| 'Unknown'` | Yes | Backend version from `/health`, otherwise `Unknown`. |
| `database` | `'connected' \| 'disconnected' \| 'Unavailable'` | Yes | Raw `/health.database` when available, otherwise `Unavailable`. |
| `qdrant` | `'connected' \| 'disconnected' \| 'collection_missing' \| 'Unavailable'` | Yes | Raw `/health.qdrant` when available, otherwise `Unavailable`. |
| `ollama` | `'connected' \| 'disconnected' \| 'Unavailable'` | Yes | Raw `/health.ollama` when available, otherwise `Unavailable`. |
| `modelName` | `string \| 'Unknown'` | Yes | Real selected chat or model-list value when available; otherwise `Unknown`. |
| `provider` | `string \| 'Unknown'` | Yes | Real selected chat provider when available; otherwise `Unknown`. |
| `ragStatus` | `'Unknown' \| 'Vector DB connected' \| 'Vector DB disconnected' \| 'Collection missing'` | Yes | Conservative label derived only from `qdrant`; never fake `Enabled`. |
| `ocrStatus` | `'Unknown' \| 'Unavailable'` | Yes | Fallback because `/health` exposes no OCR field. |
| `gpuStatus` | `'Unknown' \| 'Unavailable'` | Yes | Fallback because `/health` exposes no GPU field. |
| `lastCheckedAt` | `string \| null` | No | ISO timestamp for the latest status attempt. |
| `error` | `FrontendError \| null` | No | Friendly error when status fetch fails. |

**Validation Rules**:
- Do not display fake model names, provider names, RAG enabled states, OCR readiness, or GPU availability.
- `connected` requires a successful `/health` response with `status: 'ok'`.
- `degraded` requires a successful `/health` response with `status: 'degraded'`.
- Network or non-2xx failures must map to `state: 'disconnected'` and unavailable dependency fields.
- Status UI must include text labels and not rely on color alone.

**Relationships**:
- Rendered by `ConnectionStatusBadge` and `ConnectionStatusMenu`.
- May use selected `ChatSession.modelName` and `ChatSession.modelProvider` as real values when available.
- May be refreshed by the status service without mutating chat messages.

**State Transitions**:
- `loading -> connected` when `/health` returns `status: 'ok'`.
- `loading -> degraded` when `/health` returns `status: 'degraded'`.
- `loading -> disconnected` when the request fails.
- `connected -> degraded` when a later response reports degraded dependencies.
- `connected | degraded -> disconnected` when a later request fails.
- `disconnected -> connected | degraded` when a later request succeeds.

## Entity: WorkspaceTab

**Purpose**:
Defines one top-level workspace navigation target in the header tab bar.

**Fields**:

| Field | Type | Required | Description |
|---|---|---:|---|
| `id` | `'chat' \| 'documents' \| 'ocr' \| 'analysis' \| 'tools'` | Yes | Stable tab key. |
| `label` | `string` | Yes | Visible tab label. |
| `iconName` | `string` | Yes | Lucide icon component name or local icon identifier. |
| `isPlaceholder` | `boolean` | Yes | `true` for all non-Chat tabs in Phase 4. |
| `description` | `string` | Yes | Placeholder copy or Chat tab description. |

**Validation Rules**:
- Exactly one active tab ID exists in UI state at a time; active state is derived, not stored per tab.
- `isPlaceholder` must be `true` for Documents, OCR, Analysis, and Tools in Phase 4.
- Placeholder tab copy must not imply functional workflows are available.

**Relationships**:
- Controlled by the layout shell active tab state.
- Drives `WorkspaceContent` rendering.
- Non-Chat tabs render placeholder views only.

**State Transitions**:
- `inactive -> active` when selected by click or keyboard.
- `active -> inactive` when another tab is selected.

## Entity: StreamEvent

**Purpose**:
Represents one parsed SSE event from `POST /api/chat/{chat_id}/stream` or one parser-level failure.

**Fields**:

| Field | Type | Required | Description |
|---|---|---:|---|
| `eventName` | `'thinking_step' \| 'token' \| 'sources' \| 'done' \| 'error'` | Yes | SSE event name from the `event:` line. |
| `payload` | `unknown` | Yes | Parsed JSON data for the event. |
| `rawFrame` | `string` | Yes | Original SSE frame text for debugging without exposing to end users. |
| `receivedAt` | `string` | Yes | ISO timestamp when the frontend parsed the event. |
| `sequence` | `number` | Yes | Monotonic local order number for event application. |

**Validation Rules**:
- Frames are delimited by blank lines and must be buffered until complete.
- `data:` content must parse as JSON for known event names.
- Unknown event names are ignored or logged as frontend parse errors; they must not create fake UI states.
- `token.payload.token` must be a string.
- `done.payload.message_id` and `done.payload.chat_id` must be strings when used.
- A received `error` event marks the assistant message failed even if a later `done` event follows.

**Relationships**:
- `thinking_step` creates or updates `ThinkingStep`.
- `token` appends to assistant `Message.content`.
- `sources` replaces assistant `Message.sources` with `SourceReference[]`.
- `done` completes the assistant `Message` only if no prior error occurred.
- `error` creates a `FrontendError` for the assistant `Message`.

**State Transitions**:
- `buffering -> parsed` when a complete SSE frame is received and JSON parses.
- `buffering -> parse_failed` when a complete frame cannot be parsed.
- `parsed -> applied` when the event has updated local message state.
- `parsed_error -> failed_message` when `eventName` is `error`.

## Entity: FrontendError

**Purpose**:
Provides safe, user-facing error state for upload, chat creation, streaming, status, parsing, and UI actions.

**Fields**:

| Field | Type | Required | Description |
|---|---|---:|---|
| `code` | `'backend_unavailable' \| 'chat_create_failed' \| 'upload_validation_failed' \| 'upload_failed' \| 'stream_http_error' \| 'stream_parse_error' \| 'stream_error_event' \| 'stream_cancelled' \| 'status_unavailable' \| 'clipboard_failed'` | Yes | Stable frontend error code. |
| `message` | `string` | Yes | Friendly text safe to show to users. |
| `source` | `'chat' \| 'upload' \| 'stream' \| 'status' \| 'markdown' \| 'clipboard'` | Yes | UI area where the error occurred. |
| `retryable` | `boolean` | Yes | Whether the UI should show a retry action. |
| `occurredAt` | `string` | Yes | ISO timestamp when the error was created. |
| `httpStatus` | `number \| null` | No | HTTP status for failed backend requests when available. |
| `backendMessage` | `string \| null` | No | Sanitized backend error message when safe and useful. |

**Validation Rules**:
- `message` must not expose stack traces, raw exception dumps, local file paths, or secrets.
- `retryable` must be `false` for unsupported file type and user cancellation.
- Stream retries after tokens have started must be user-triggered only; never auto-retry.
- `backendMessage` must be concise and sanitized before display.

**Relationships**:
- May be attached to `Message`, `AttachedFile`, or `ConnectionStatus`.
- May be produced while parsing a `StreamEvent`.
- Drives retry, remove-file, or troubleshooting UI actions.

**State Transitions**:
- `created -> displayed` when rendered in the relevant component.
- `displayed -> retrying` when the user chooses a retryable action.
- `displayed -> dismissed` when the user removes the failed attachment, retries successfully, changes input, or closes an error affordance.
