# Implementation Plan: Frontend Core UI

**Branch**: `specs/004-frontend-core-ui` | **Date**: 2026-05-31 | **Spec**: `specs/004-frontend-core-ui/spec.md`
**Input**: Feature specification from `/specs/004-frontend-core-ui/spec.md`

## Summary

Build the Phase 4 core frontend as a React application under `frontend/src`. The UI delivers a Claude-inspired industrial assistant workspace with a fixed desktop shell, local-only chat/sidebar sessions, polished tab navigation, pre-send attachment upload, backend chat creation via `POST /api/chats`, browser-native `fetch` streaming to `POST /api/chat/{chat_id}/stream`, progressive thinking steps, markdown answer rendering, source chips, status visibility, error recovery, and reduced-motion-aware interactions. Documents, OCR, Analysis, and Tools remain polished placeholder views only in Phase 4.

## Branch And Path Decision

The correct feature identity is `004-frontend-core-ui` because the active feature directory, specification, and user request all target `specs/004-frontend-core-ui`. The previously reported Git branch `specs/005-frontend-core-ui` was renamed to `specs/004-frontend-core-ui` so branch and artifact paths are aligned.

## Technical Context

**Language/Version**: React with TypeScript/JavaScript under `frontend/src`; current repository frontend is Streamlit/Python and has no confirmed React toolchain yet  
**Primary Dependencies**: React, browser `fetch` and `ReadableStream`, Lucide icons, frontend test tooling to be added or reused if present, and markdown rendering only after confirming no existing renderer is already present  
**Storage**: Local frontend state only for chat sessions, active session, messages, streaming state, attached file previews, uploaded attachment references, active tab, sidebar search, and status cache  
**Testing**: Frontend unit/component tests plus manual quickstart validation for streaming, uploads, placeholder tabs, status, markdown, reduced motion, and error states  
**Target Platform**: Desktop web browsers at 1280px width and above  
**Project Type**: Web application frontend integrated with existing FastAPI backend  
**Performance Goals**: Stream tokens progressively without visible layout jank; hover feedback within 200ms; sidebar search updates within 300ms after debounce; tab transitions finish within 500ms; input remains responsive during stream updates  
**Constraints**: Use React under `frontend/src`; do not implement Streamlit; do not call nonexistent `POST /api/chat/stream`; create or reuse a backend chat ID before calling `POST /api/chat/{chat_id}/stream`; do not use EventSource-only GET unless the verified backend contract explicitly requires it and the plan is updated first; do not use Python `httpx` or `httpx-sse` in frontend; upload attachments before opening chat stream; include only backend-returned attachment references in the chat stream body; keep non-Chat tabs as placeholders; keep chat/sidebar history local only; respect `prefers-reduced-motion`; do not invent backend endpoints, schemas, events, or successful states  
**Scale/Scope**: Phase 4 covers one desktop UI shell, one primary Chat workflow, four placeholder workspace tabs, local session management, and integrations with existing backend chat, upload, and status endpoints

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Code quality**: PASS. Plan keeps one UI concept per component file, small service functions, named design tokens, no dead code, and no premature abstraction.
- **Naming and organization**: PASS. React components use clear PascalCase names, hooks/services use specific verb/noun names, and source is contained under `frontend/src`.
- **Type safety and I/O boundaries**: PASS. Stream events, upload responses, status responses, and local state entities are documented in `data-model.md` and `contracts/` for typed frontend boundaries.
- **Error handling**: PASS. Plan requires friendly UI errors for stream drops, upload failures, backend disconnection, parse failures, and retryable chat sends without exposing stack traces.
- **Dependency management**: PASS. New frontend libraries are limited to necessary markdown/code-copy support and must be checked against existing frontend dependencies before installation.
- **Configuration**: PASS. Backend base URL must come from the existing frontend environment/config pattern, not hardcoded in components.
- **Streaming discipline**: PASS. Frontend reads incrementally with `ReadableStream` and closes on backend `done`; it does not buffer full responses before render.
- **Testing**: PASS. Tasks include component/service tests and manual validation through `quickstart.md`.

## Backend Contract Verification Before Implementation

Before writing any UI integration code, inspect the existing backend routes and confirm the real contracts for:

- Chat stream endpoint path.
- Chat stream HTTP method.
- Chat stream request body schema.
- Chat stream response format.
- Whether the stream uses SSE-style frames, NDJSON, or another chunk format.
- Event schema for `thinking_step`.
- Event schema for `token`.
- Event schema for `sources`.
- Event schema for `done`.
- Event schema for `error`.
- File upload endpoint path.
- File upload method.
- File upload request format.
- File upload accepted types.
- File upload response schema.
- Exact attachment reference shape expected by the chat stream endpoint.
- Status/health endpoint path.
- Status/health response schema for backend connection.
- Status/health response schema for model name.
- Status/health response schema for provider.
- Status/health response schema for RAG enabled.
- Status/health response schema for Qdrant.
- Status/health response schema for OCR readiness.
- Status/health response schema for GPU status if available.
- CORS/config requirements for frontend-to-backend requests.

Strict rule: If any backend contract is missing, unclear, or mismatched, stop and report the mismatch. Do not invent fake endpoints, fake schemas, mock responses, or frontend-only assumptions.

## React Dev-Server CORS Note

The current backend CORS configuration is known to allow the existing Streamlit origin:

- `http://localhost:8501`

The new React/Vite dev server will commonly run on:

- `http://localhost:5173`

Because backend changes require explicit user approval, Phase 4 implementation must prefer a frontend-only Vite proxy workaround first.

Preferred development approach:

- Run the React/Vite dev server on `http://localhost:5173`.
- Configure Vite dev proxy so frontend calls to `/api/*` and `/health` are proxied to the FastAPI backend, usually `http://localhost:8001`.
- Frontend service code should call relative paths such as `/api/chats`, `/api/chat/{chat_id}/stream`, `/api/ingest/pdf`, `/api/ingest/audio`, `/api/ingest/image`, and `/health` when running through the Vite proxy.
- Do not modify backend CORS/config unless the proxy approach is insufficient and the user explicitly approves a backend/config change.

Stop condition:

If browser requests are blocked by CORS and the Vite proxy is not configured or does not solve the issue, stop and request user approval before modifying backend CORS/config.

## Frontend Project Inspection Before Dependency Changes

Before adding or changing dependencies, inspect:

- `frontend/package.json`.
- Frontend build tool: Vite, Next, CRA, or other.
- Existing TypeScript setup.
- Existing `frontend/src` structure.
- Existing styling approach.
- Existing test runner.
- Existing testing utilities.
- Existing API/config pattern.
- Existing environment variable pattern.

Strict rule: Use the existing project conventions wherever possible. Do not install new libraries until the existing frontend structure and dependencies are inspected.

## Markdown Rendering Decision

- Prefer `react-markdown` with `remark-gfm` only if no existing markdown renderer is already used.
- Use custom component mappings for headings, strong text, inline code, fenced code blocks, tables, lists, links, and blockquotes if needed.
- Use a custom `CodeBlock` component for dark code block styling, language label if available, copy button, and copied/error feedback.
- Do not render unsafe raw HTML unless sanitization is added and explicitly approved.

## Styling Strategy

- Use the existing frontend styling approach if already present.
- If no styling system exists, use plain CSS with design tokens under `frontend/src/styles`.
- Do not introduce Tailwind, styled-components, Material UI, Chakra UI, or any heavy UI framework unless already present or explicitly approved.
- Keep the design system local, readable, and easy to modify.

## Attachment-Only Send Decision

For Phase 4, a chat message requires non-empty text. Attachment-only messages are out of scope unless the current feature specification explicitly requires them.

## No Mock/Fake API Rule

Do not fake successful backend status, model connection, Qdrant availability, OCR readiness, upload success, or chat streaming events. If real backend data is unavailable, show a graceful unknown/disconnected/unavailable state.

## Implementation Stop Conditions

Stop and report before implementation if:

- Any implementation task still assumes `POST /api/chat/stream` instead of the verified `POST /api/chats` then `POST /api/chat/{chat_id}/stream` flow.
- Browser CORS blocks the intended React dev-server origin and the user has not approved a backend/config change.
- Stream response format is not confirmed.
- Event payload schemas are unknown.
- Upload endpoint is missing.
- Upload response schema is unknown.
- Attachment reference shape is unknown.
- Status endpoint is missing or incomplete.
- Frontend build/test setup is unclear.
- Required dependencies conflict with existing frontend setup.

## Project Structure

### Documentation (this feature)

```text
specs/004-frontend-core-ui/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── chat-stream.md
│   ├── file-upload.md
│   └── status.md
└── tasks.md
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── components/
│   │   ├── chat/
│   │   ├── layout/
│   │   ├── markdown/
│   │   ├── sidebar/
│   │   ├── status/
│   │   ├── tabs/
│   │   └── ui/
│   ├── hooks/
│   ├── services/
│   ├── styles/
│   ├── types/
│   └── test/
└── tests/

backend/
├── api/
│   └── routes/
└── main.py
```

**Structure Decision**: Implement Phase 4 as a new React frontend under `frontend/src` because the current frontend is Streamlit/Python. Backend source is not changed in this phase unless later task validation discovers a contract mismatch that the user explicitly approves fixing.

## Component Architecture

### Layout Components

- `AppShell`: top-level desktop shell with fixed sidebar, workspace column, active tab state, and status area.
- `WorkspaceHeader`: tab bar on the left and connection status on the right.
- `WorkspaceContent`: routes active tab to Chat or polished placeholder content without adding a router requirement unless the existing frontend already uses one.
- `PlaceholderView`: reusable non-Chat tab placeholder for Documents, OCR, Analysis, and Tools with icon, title, short description, and future-scope affordance.

### Sidebar Components

- `Sidebar`: 280px fixed-width navigation area with logo header, New Chat button, search, local chat list, sections, and settings footer.
- `LogoMark`: animated starburst icon reused by sidebar, AI message headers, and thinking card headers.
- `ChatSearch`: debounced 200ms input that filters local chat sessions.
- `ChatList`: displays local sessions, active marker, relative timestamp, empty state, and selected chat callback.
- `SidebarSection`: collapsible visual sections for Projects, Knowledge Bases, and Tools with placeholder content only.

### Chat Components

- `ChatWorkspace`: active conversation surface, scroll container, empty state, message list, and sticky input bar.
- `MessageList`: ordered rendering of user and assistant messages with stable keys and auto-scroll during streaming.
- `UserMessageCard`: avatar, timestamp, text, and attached file chips.
- `AssistantMessageCard`: thinking card, markdown response, stream cursor, source chips, and hover actions.
- `ThinkingCard`: receives ordered thinking steps and manages auto-expand/collapse behavior.
- `SourceChips`: renders up to 3 visible sources and a `+N more` chip.
- `InputBar`: attach/audio/tools/model controls, expandable textarea, send button, Enter/Shift+Enter behavior, and disabled state.
- `AttachmentTray`: preview chips, image thumbnails, remove actions, upload progress and errors.

### Markdown Components

- `MarkdownRenderer`: wraps selected markdown renderer with design-system classes for headings, bold text, lists, links, tables, inline code, and code blocks.
- `CodeBlock`: dark code surface with language label when available and copy button with copied/error feedback.

### Status Components

- `ConnectionStatusBadge`: compact green/red status, provider, model, and RAG state.
- `ConnectionStatusMenu`: expanded backend, model, Qdrant, OCR, and GPU details with troubleshooting hints when disconnected.

## Frontend Service Layer Plan

- `services/chatStreamService`: creates a backend chat with `POST /api/chats` when needed, sends `fetch` requests to `POST /api/chat/{chat_id}/stream`, reads `response.body` with a `ReadableStreamDefaultReader`, decodes chunks with `TextDecoder`, parses confirmed SSE event frames, and emits typed callbacks for `thinking_step`, `token`, `sources`, `done`, and `error` only after schemas are verified.
- `services/fileUploadService`: uploads pending `File` objects before chat send, validates accepted file types against the verified upload contract, maps backend responses into stable `AttachedFile` references, and surfaces per-file failures.
- `services/statusService`: fetches current backend/model/Qdrant/OCR status from the verified status endpoint for the header indicator and maps missing/unreachable backend responses to disconnected or unknown UI state.
- `services/timeService`: formats relative timestamps for local sessions without persisting data.
- Service functions return typed results and throw typed frontend errors or return discriminated result objects; UI components translate failures into friendly messages.

## State Management Plan

- Keep Phase 4 state local to React using component state and small custom hooks; do not add a global state library unless the existing frontend already has one.
- `useChatSessions`: owns local `ChatSession[]`, active session ID, New Chat creation, first-message title generation, message append/update, and search filtering.
- `useChatStream`: owns streaming lifecycle, `AbortController`, assistant placeholder message creation, token append, thinking step updates, source finalization, done state, stream errors, and retry metadata.
- `useAttachments`: owns selected local files, preview URLs, validation, removal, upload progress, uploaded references, and cleanup of object URLs.
- `useConnectionStatus`: polls or refreshes status using the existing project pattern, caches last successful status, and exposes connected/disconnected/loading states.
- `useReducedMotion`: wraps `window.matchMedia('(prefers-reduced-motion: reduce)')` and exposes a boolean for animation-sensitive component behavior.
- Local state is reset on browser refresh; backend-persisted chat CRUD is explicitly out of scope.

## Streaming Implementation Plan

1. User submits non-empty text from `InputBar`.
2. If files are pending, `fileUploadService.uploadAttachments()` runs first.
3. If upload succeeds, create a local user `Message` with uploaded attachment references and create an empty streaming assistant `Message`.
4. `chatStreamService.streamChat()` ensures a backend chat exists, then opens `fetch()` to `POST /api/chat/{chat_id}/stream` with `query`, optional model fields, and returned attachment file IDs.
5. Read `response.body` incrementally with `ReadableStream` and `TextDecoder`.
6. Parse backend event frames into typed events. Supported events are `thinking_step`, `token`, `sources`, `done`, and `error`.
7. For `thinking_step`, insert or update the matching `ThinkingStep` in the assistant message.
8. For `token`, append text to the assistant markdown buffer and keep the stream cursor visible.
9. For `sources`, replace assistant source references with parsed source chips.
10. For `done`, mark the assistant message complete, hide the cursor, close the reader, and auto-collapse thinking after 2 seconds.
11. If network, parse, or backend error occurs, mark the assistant message as failed and offer retry for the last user message.

## File Upload Before Chat Send Sequence

```text
User selects files
  -> frontend validates type and size for preview eligibility
  -> preview chips render from local File objects
User clicks Send
  -> disable Send and show upload progress
  -> POST files to upload endpoint
  -> receive backend attachment references
  -> store references on local user message
  -> open verified chat stream endpoint with only backend-returned attachment references
  -> clear pending local files after stream starts successfully
```

- Upload failures block the chat stream and keep the user text/files in the input area for correction or retry.
- Partial upload failure is treated as failed send unless the backend contract explicitly returns successful references for all selected files.
- Object URLs for image previews are revoked when attachments are removed or sent.

## Error Handling Strategy

- Empty message: disable Send unless text has non-whitespace content or future scope allows attachment-only sends.
- Upload validation failure: show inline attachment error and do not call backend.
- Upload network/backend failure: show retryable inline error, retain text and selected files.
- Stream open failure: mark assistant placeholder failed, keep retry action available.
- Mid-stream drop: preserve received tokens, show interrupted state, and offer retry last user message.
- Stream event parse failure: show friendly malformed-stream error and stop current stream to avoid corrupt UI.
- Backend disconnected: status indicator turns red and chat send is blocked or clearly warns before attempt.
- Markdown render failure: fall back to escaped plain text for the message body.
- Copy failure: show non-blocking copy error feedback near the code block/action button.

## Testing Strategy

- Unit test stream frame parsing with split chunks, multiple events per chunk, unknown event types, error events, and final `done`.
- Unit test attachment validation, upload success mapping, upload failure behavior, object URL cleanup, and send gating.
- Component test sidebar session creation, active session highlighting, relative timestamps, empty state, and debounced search.
- Component test Chat workflow with mocked streaming callbacks for thinking steps, tokens, sources, done, and mid-stream error.
- Component test MarkdownRenderer styling hooks for headings, bold, inline code, code blocks, tables, lists, links, and copy button behavior.
- Component test tab switching and placeholder views.
- Component test connection status for connected, disconnected, loading, and expanded detail states.
- Accessibility test keyboard send behavior, focus states, button labels, status semantics, and reduced-motion behavior.
- Manual quickstart validation covers backend/frontend startup, streaming, attachments, reduced motion, placeholder tabs, and status.

## Accessibility And Reduced-Motion Strategy

- All interactive elements use real buttons/inputs with visible focus states and accessible labels.
- Chat input supports Enter to send and Shift+Enter for newline without trapping keyboard focus.
- Status indicator exposes readable text in addition to color; green/red dots are not the only signal.
- Thinking step updates should use polite live region behavior only where it does not overwhelm screen readers.
- Source chips and hover actions remain keyboard accessible, not hover-only.
- CSS uses `@media (prefers-reduced-motion: reduce)` to set transition/animation durations near zero and disable continuous starburst rotation/breathing.
- Components using timers or animation state consult `useReducedMotion` to skip delayed auto-animation where appropriate while preserving functionality.

## Implementation Sequencing

1. Confirm backend route contracts and existing frontend dependency/test setup; stop before implementation on any contract mismatch or dependency conflict.
2. Add design tokens, base layout CSS, and reduced-motion CSS baseline.
3. Build `AppShell`, sidebar, header, tabs, and placeholder views.
4. Define frontend types for sessions, messages, stream events, attachments, sources, status, and tabs.
5. Add local session state hook and sidebar chat behavior.
6. Build Chat workspace, message cards, input bar, and attachment preview tray.
7. Add file upload service and connect upload-before-stream send flow.
8. Add chat streaming service and stream event parser.
9. Connect thinking card, token rendering, source chips, done state, and retry errors.
10. Add markdown renderer and code block copy handling.
11. Add connection status service and indicator/dropdown.
12. Add tests for services, hooks, and core components.
13. Run quickstart/manual validation and polish spacing, motion, focus, and error states.

## Post-Design Constitution Check

- **Scope control**: PASS. Non-Chat tabs remain placeholders, backend-persisted chat history remains out of scope, and implementation tasks are split into small ordered units.
- **Maintainability**: PASS. Component/service boundaries match one concept per file and avoid a heavy global state library.
- **Typed boundaries**: PASS. Contracts and data model define all backend-facing and state-facing structures needed before implementation.
- **User-facing errors**: PASS. Error strategy maps technical failures to safe UI messages.
- **Accessibility**: PASS. Reduced motion, keyboard behavior, focus states, and non-color status cues are explicit planning requirements.

## Complexity Tracking

No constitution violations identified.
