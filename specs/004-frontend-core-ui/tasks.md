# Tasks: Frontend Core UI

**Input**: `specs/004-frontend-core-ui/spec.md`, `plan.md`, `research.md`, `data-model.md`, and `contracts/`  
**Scope**: Implementation tasks for the React Phase 4 frontend only. Do not start backend changes unless the user explicitly approves resolving a confirmed backend mismatch.  
**Contract rule**: Use `POST /api/chats` before `POST /api/chat/{chat_id}/stream`. Do not call nonexistent `POST /api/chat/stream`.

## Phase 1: Project Inspection And Safety Checks

- [x] T001 [Phase 1] [Project Inspection] Verify current frontend shape
  - Files: `frontend/`, `frontend/package.json`, `frontend/src/`
  - Action: Confirm whether `package.json`, `src/`, Vite config, and test config exist before adding files.
  - Expected output: A short implementation note listing which frontend files were missing or present.
  - Validation: No source file is modified during this inspection task.

- [x] T002 [Phase 1] [Project Inspection] Verify backend contract files before implementation
  - Files: `specs/004-frontend-core-ui/contracts/chat-stream.md`, `specs/004-frontend-core-ui/contracts/file-upload.md`, `specs/004-frontend-core-ui/contracts/status.md`
  - Action: Re-read the three contract files and record the exact endpoints, methods, event names, and fallback rules in implementation notes.
  - Expected output: Implementation notes confirm `/api/chats`, `/api/chat/{chat_id}/stream`, `/api/ingest/pdf`, `/api/ingest/audio`, `/api/ingest/image`, and `/health`.
  - Validation: Notes contain no `/api/chat/stream` usage except as a documented mismatch.

- [x] T003 [Phase 1] [Safety Checks] Verify no Streamlit implementation path is used for Phase 4
  - Files: `frontend/app.py`, `frontend/utils/api_client.py`, `frontend/src/`
  - Action: Confirm Streamlit files remain untouched and React implementation will live under `frontend/src`.
  - Expected output: React files are planned under `frontend/src`; existing Streamlit files remain unchanged.
  - Validation: `git diff -- frontend/app.py frontend/utils/api_client.py` shows no Phase 4 React changes.

- [x] T004 [Phase 1] [Safety Checks] Check React dev-server CORS risk
  - Files: `backend/api/routes/chat.py`, `specs/004-frontend-core-ui/contracts/chat-stream.md`
  - Action: Confirm whether the intended React dev origin is accepted by backend CORS before relying on browser requests.
  - Expected output: Implementation note either confirms the chosen origin is allowed or marks CORS as blocked pending user-approved backend/config change.
  - Validation: If CORS is not allowed, do not modify backend; stop and request user approval for the backend/config change.

## Phase 2: Dependency Decisions

- [x] T005 [Phase 2] [Dependency Decisions] Create minimal React package manifest if absent
  - Files: `frontend/package.json`
  - Action: If no manifest exists, create a minimal React/Vite package manifest with scripts for `dev`, `build`, `test`, and `lint`; otherwise preserve existing conventions.
  - Expected output: `frontend/package.json` exists with explicit frontend scripts.
  - Validation: `npm run` from `frontend/` lists the expected scripts.

- [x] T006 [P] [Phase 2] [Dependency Decisions] Create TypeScript and Vite configuration if absent
  - Files: `frontend/tsconfig.json`, `frontend/tsconfig.node.json`, `frontend/vite.config.ts`
  - Action: Add minimal configs only if missing, using React and browser-native streaming.
  - Expected output: Vite can resolve `frontend/src/main.tsx` as the app entry.
  - Validation: Config files contain no backend URL hardcoding and no Streamlit references.

- [x] T007 [P] [Phase 2] [Dependency Decisions] Create frontend HTML entry if absent
  - Files: `frontend/index.html`
  - Action: Add the Vite root HTML with a single `#root` mount node when missing.
  - Expected output: Browser entry can mount the React app.
  - Validation: `frontend/index.html` contains `id="root"` exactly once.

- [x] T008 [Phase 2] [Dependency Decisions] Add only approved UI dependencies
  - Files: `frontend/package.json`
  - Action: Add React, React DOM, Lucide icons, markdown renderer, GFM plugin, and test dependencies only if absent and needed.
  - Expected output: Dependencies support React rendering, icons, markdown, and tests without a heavy UI framework.
  - Validation: `package.json` contains no Tailwind, Material UI, Chakra UI, styled-components, or unapproved heavy framework.

- [x] T009 [P] [Phase 2] [Dependency Decisions] Add frontend environment example
  - Files: `frontend/.env.example`, `frontend/src/config.ts`
  - Action: Document and read `VITE_BACKEND_BASE_URL`, defaulting safely to `http://localhost:8001` only in config code.
  - Expected output: One typed config module exposes the backend base URL.
  - Validation: Components import backend URL from `frontend/src/config.ts`, not directly from environment variables.

## Phase 3: Design Tokens And Base Styles

- [x] T010 [Phase 3] [Design Tokens] Create design token CSS
  - Files: `frontend/src/styles/tokens.css`
  - Action: Define color, typography, spacing, radius, shadow, z-index, and motion variables for the Phase 4 UI.
  - Expected output: Reusable CSS variables cover shell, sidebar, chat cards, status, tabs, and errors.
  - Validation: No component file contains duplicate hardcoded token palettes.

- [x] T011 [P] [Phase 3] [Base Styles] Create global reset and focus styles
  - Files: `frontend/src/styles/global.css`
  - Action: Add base box sizing, body styles, font stack, scrollbar styling, buttons, inputs, and visible focus states.
  - Expected output: App has consistent base styling before component CSS is added.
  - Validation: Keyboard focus is visible for buttons, inputs, tabs, and menu triggers.

- [x] T012 [P] [Phase 3] [Reduced Motion] Add reduced-motion CSS baseline
  - Files: `frontend/src/styles/motion.css`
  - Action: Add `prefers-reduced-motion: reduce` rules that minimize animations and transitions.
  - Expected output: Decorative motion can be disabled globally.
  - Validation: CSS includes a media query for `prefers-reduced-motion: reduce`.

- [x] T013 [Phase 3] [Base Styles] Import base styles in app entry
  - Files: `frontend/src/main.tsx`
  - Action: Import token, global, and motion styles once at the React entry point.
  - Expected output: Styles are loaded for the full app.
  - Validation: Style imports appear only in the app entry or top-level stylesheet aggregator.

## Phase 4: Layout Shell

- [x] T014 [Phase 4] [Layout Shell] Create React app entry component
  - Files: `frontend/src/App.tsx`, `frontend/src/main.tsx`
  - Action: Mount `AppShell` from `App.tsx` through `main.tsx` using React.
  - Expected output: Empty shell renders without Streamlit.
  - Validation: Running the frontend dev server shows the React root without console mount errors.

- [x] T015 [P] [Phase 4] [Layout Shell] Create app shell component
  - Files: `frontend/src/components/layout/AppShell.tsx`, `frontend/src/components/layout/AppShell.css`
  - Action: Build the fixed 280px sidebar column and main workspace column.
  - Expected output: Desktop layout fits screens 1280px and wider.
  - Validation: Sidebar width is fixed at 280px and main content does not overlap it.

- [x] T016 [P] [Phase 4] [Layout Shell] Create workspace header component
  - Files: `frontend/src/components/layout/WorkspaceHeader.tsx`, `frontend/src/components/layout/WorkspaceHeader.css`
  - Action: Add the top header container with left tab slot and right status slot.
  - Expected output: Header can host tabs and status without coupling to chat logic.
  - Validation: Header renders with semantic landmark or accessible label.

- [x] T017 [Phase 4] [Layout Shell] Create workspace content switcher
  - Files: `frontend/src/components/layout/WorkspaceContent.tsx`
  - Action: Render Chat for `chat` tab and placeholder views for non-Chat tabs.
  - Expected output: Active tab controls visible workspace content.
  - Validation: Switching active tab changes content without using a router.

## Phase 5: Sidebar

- [x] T018 [P] [Phase 5] [Sidebar] Create logo mark component
  - Files: `frontend/src/components/ui/LogoMark.tsx`, `frontend/src/components/ui/LogoMark.css`
  - Action: Implement the starburst logo with reduced-motion-safe classes.
  - Expected output: Reusable logo renders in sidebar and assistant/thinking headers.
  - Validation: Reduced motion disables continuous rotation and pulse.

- [x] T019 [Phase 5] [Sidebar] Create sidebar shell
  - Files: `frontend/src/components/sidebar/Sidebar.tsx`, `frontend/src/components/sidebar/Sidebar.css`
  - Action: Add logo header, New Chat button, chat section, Projects, Knowledge Bases, Tools, and Settings footer.
  - Expected output: Sidebar matches Phase 4 structure with placeholder non-chat sections.
  - Validation: Sidebar is keyboard navigable and contains no functional deferred workflows.

- [x] T020 [P] [Phase 5] [Sidebar] Create chat search component
  - Files: `frontend/src/components/sidebar/ChatSearch.tsx`
  - Action: Build a controlled search input with a 200ms debounced callback.
  - Expected output: Search text updates local filtering without backend calls.
  - Validation: Typing filters only after the debounce interval in tests or manual check.

- [x] T021 [P] [Phase 5] [Sidebar] Create chat list component
  - Files: `frontend/src/components/sidebar/ChatList.tsx`, `frontend/src/components/sidebar/ChatList.css`
  - Action: Render local chat titles, active state, relative timestamps, and empty state.
  - Expected output: Chat list supports selection and displays `No conversations yet` when empty.
  - Validation: Active item has a text/visual state beyond color alone.

- [x] T022 [P] [Phase 5] [Sidebar] Create sidebar section component
  - Files: `frontend/src/components/sidebar/SidebarSection.tsx`
  - Action: Render static placeholder section rows for Projects, Knowledge Bases, and Tools.
  - Expected output: Sections look polished but do not perform real workflows.
  - Validation: Clicking placeholder rows does not call backend endpoints.

## Phase 6: Tabs And Placeholder Views

- [x] T023 [Phase 6] [Tabs] Define workspace tab constants
  - Files: `frontend/src/types/workspace.ts`, `frontend/src/components/tabs/workspaceTabs.ts`
  - Action: Define Chat, Documents, OCR, Analysis, and Tools tab metadata matching `WorkspaceTab`.
  - Expected output: One source of truth exists for tab IDs, labels, icons, and placeholder flags.
  - Validation: Non-Chat tabs have `isPlaceholder: true`.

- [x] T024 [P] [Phase 6] [Tabs] Create tab bar component
  - Files: `frontend/src/components/tabs/WorkspaceTabs.tsx`, `frontend/src/components/tabs/WorkspaceTabs.css`
  - Action: Build accessible tab buttons with active underline, hover states, and keyboard support.
  - Expected output: Tab switching updates active tab state in `AppShell`.
  - Validation: Tabs expose `role="tab"` or equivalent accessible button semantics.

- [x] T025 [P] [Phase 6] [Placeholder Views] Create reusable placeholder view
  - Files: `frontend/src/components/tabs/PlaceholderView.tsx`, `frontend/src/components/tabs/PlaceholderView.css`
  - Action: Add icon, title, short description, and future-scope label for non-Chat tabs.
  - Expected output: Documents, OCR, Analysis, and Tools can share the placeholder component.
  - Validation: Placeholder copy does not claim real upload, OCR, analysis, or tools functionality.

- [x] T026 [Phase 6] [Placeholder Views] Wire placeholder tabs into workspace content
  - Files: `frontend/src/components/layout/WorkspaceContent.tsx`
  - Action: Render the placeholder view for each non-Chat tab.
  - Expected output: All five tabs are navigable with Chat as the only functional workspace.
  - Validation: Manual tab clicks show the correct placeholder title.

## Phase 7: Frontend Types

- [x] T027 [Phase 7] [Frontend Types] Add chat and message types
  - Files: `frontend/src/types/chat.ts`
  - Action: Define `ChatSession`, `Message`, `ThinkingStep`, `SourceReference`, `StreamEvent`, and related unions from `data-model.md`.
  - Expected output: Chat state and stream handlers share typed entities.
  - Validation: Type definitions include `backendChatId` and do not include `/api/chat/stream` assumptions.

- [x] T028 [P] [Phase 7] [Frontend Types] Add attachment types
  - Files: `frontend/src/types/attachments.ts`
  - Action: Define `AttachedFile`, `UploadedAttachmentReference`, upload result, MIME category, and upload status types.
  - Expected output: Upload UI and service use the same attachment contract.
  - Validation: `UploadedAttachmentReference.file_id` is typed as the value sent in `attached_files`.

- [x] T029 [P] [Phase 7] [Frontend Types] Add status and error types
  - Files: `frontend/src/types/status.ts`, `frontend/src/types/errors.ts`
  - Action: Define `ConnectionStatus`, status response shape, and `FrontendError` codes.
  - Expected output: Status service and UI can represent `Unknown` and `Unavailable` safely.
  - Validation: Types do not require active model, provider, OCR, GPU, or RAG enabled fields from `/health`.

- [x] T030 [P] [Phase 7] [Frontend Types] Add API response types
  - Files: `frontend/src/types/api.ts`
  - Action: Define `CreateChatResponse`, `HealthResponse`, upload response shapes, and stream request body.
  - Expected output: Service functions have typed I/O boundaries.
  - Validation: Stream request body uses `query` and `attached_files`, not `message` or local file objects.

## Phase 8: Local Chat Session Hook

- [x] T031 [Phase 8] [Local Chat Session Hook] Implement chat session state hook
  - Files: `frontend/src/hooks/useChatSessions.ts`
  - Action: Manage local sessions, active session ID, New Chat creation, selection, and updated timestamps.
  - Expected output: Sidebar and Chat workspace can read and update local chat state.
  - Validation: Creating a new chat does not call backend until the first send requires streaming.

- [x] T032 [P] [Phase 8] [Local Chat Session Hook] Add title generation helper
  - Files: `frontend/src/services/timeService.ts`, `frontend/src/hooks/useChatSessions.ts`
  - Action: Generate a title from the first user message and format relative timestamps.
  - Expected output: Sidebar shows readable titles and relative times.
  - Validation: Empty chats display `New chat` and message-derived titles are trimmed.

- [x] T033 [Phase 8] [Local Chat Session Hook] Add message mutation helpers
  - Files: `frontend/src/hooks/useChatSessions.ts`
  - Action: Add helpers to append user messages, create assistant placeholders, append tokens, set sources, set thinking steps, complete, fail, and cancel messages.
  - Expected output: Stream service callbacks can update messages through one local state boundary.
  - Validation: Message updates preserve order and never mutate state in place.

## Phase 9: Attachment Hook And Preview UI

- [x] T034 [Phase 9] [Attachment Hook] Implement attachment state hook
  - Files: `frontend/src/hooks/useAttachments.ts`
  - Action: Manage selected files, validation state, removal, upload progress, uploaded references, and cleanup.
  - Expected output: Input bar can display and update pending attachments.
  - Validation: Removing an image revokes its object URL.

- [x] T035 [P] [Phase 9] [Attachment Preview UI] Create attachment tray component
  - Files: `frontend/src/components/chat/AttachmentTray.tsx`, `frontend/src/components/chat/AttachmentTray.css`
  - Action: Render selected files, thumbnails for images, upload status, error messages, and remove buttons.
  - Expected output: Users can inspect and remove selected files before send.
  - Validation: Unsupported or failed files show text errors and are not silently hidden.

- [x] T036 [P] [Phase 9] [Attachment Preview UI] Create file picker control
  - Files: `frontend/src/components/chat/FileAttachButton.tsx`
  - Action: Add a button and hidden file input accepting PDF, image, and audio MIME types from the upload contract.
  - Expected output: File picker supports multiple selected supported files.
  - Validation: `accept` contains only MIME types documented in `contracts/file-upload.md`.

- [x] T037 [Phase 9] [Attachment Hook] Enforce attachment count and size rules
  - Files: `frontend/src/hooks/useAttachments.ts`, `frontend/src/types/attachments.ts`
  - Action: Enforce supported MIME types, known size limits, and `MAX_ATTACHED_FILES` default 10.
  - Expected output: Invalid files are rejected before upload with friendly errors.
  - Validation: Failed validation prevents the file ID from appearing in `attached_files`.

## Phase 10: File Upload Service

- [x] T038 [Phase 10] [File Upload Service] Implement endpoint selection by MIME type
  - Files: `frontend/src/services/fileUploadService.ts`
  - Action: Map PDFs to `/api/ingest/pdf`, audio to `/api/ingest/audio`, and images to `/api/ingest/image`.
  - Expected output: Each file uploads to the correct type-specific endpoint.
  - Validation: Unsupported MIME types return a validation error before `fetch`.

- [x] T039 [Phase 10] [File Upload Service] Implement single-file multipart upload
  - Files: `frontend/src/services/fileUploadService.ts`
  - Action: Send one `multipart/form-data` request with field `file` for each selected file.
  - Expected output: Upload responses map to `UploadedAttachmentReference`.
  - Validation: Request body never includes multiple files in one backend call.

- [x] T040 [Phase 10] [File Upload Service] Implement multi-file upload orchestration
  - Files: `frontend/src/services/fileUploadService.ts`, `frontend/src/hooks/useAttachments.ts`
  - Action: Upload multiple files as separate requests and preserve successful references when another upload fails.
  - Expected output: UI can show uploaded and failed files separately.
  - Validation: Chat send is blocked until failed files are removed or retried.

- [x] T041 [P] [Phase 10] [File Upload Service] Normalize upload errors
  - Files: `frontend/src/services/fileUploadService.ts`, `frontend/src/types/errors.ts`
  - Action: Map unsupported media, payload too large, validation, network, and global backend errors to `FrontendError`.
  - Expected output: Upload errors are friendly and safe to display.
  - Validation: Raw stack traces and local file paths are not displayed.

## Phase 11: Chat Stream Parser

- [x] T042 [Phase 11] [Chat Stream Parser] Create SSE frame parser
  - Files: `frontend/src/services/chatStreamParser.ts`
  - Action: Buffer chunks until blank-line frame delimiters and parse `event:` plus one or more `data:` lines.
  - Expected output: Parser emits typed `StreamEvent` objects from SSE frames.
  - Validation: Split chunks and multiple frames per chunk parse correctly.

- [x] T043 [Phase 11] [Chat Stream Parser] Validate known stream event payloads
  - Files: `frontend/src/services/chatStreamParser.ts`
  - Action: Validate `thinking_step`, `token`, `sources`, `done`, and `error` payload shapes.
  - Expected output: Invalid known events produce `stream_parse_error` instead of corrupting UI state.
  - Validation: `token` requires string `token`; `done` requires string `message_id` and `chat_id` before use.

- [x] T044 [P] [Phase 11] [Chat Stream Parser] Ignore unknown SSE events safely
  - Files: `frontend/src/services/chatStreamParser.ts`
  - Action: Handle unknown `event:` values without throwing or rendering fake data.
  - Expected output: Unknown events are ignored or returned as non-applied parser notices.
  - Validation: Unknown events do not append assistant text or mark messages complete.

- [x] T045 [P] [Phase 11] [Chat Stream Parser] Add parser tests
  - Files: `frontend/src/services/chatStreamParser.test.ts`
  - Action: Test split chunks, multi-line data, multiple events per chunk, malformed JSON, error event, and done event.
  - Expected output: Parser behavior is locked before service integration.
  - Validation: Test command passes for parser tests.

## Phase 12: Chat Stream Service

- [x] T046 [Phase 12] [Chat Stream Service] Implement backend chat creation service
  - Files: `frontend/src/services/chatStreamService.ts`
  - Action: Add `createBackendChat` that calls `POST /api/chats` and returns `id`, title, provider, and model from the real response.
  - Expected output: A local chat can obtain `backendChatId` before streaming.
  - Validation: Service never opens `/api/chat/{chat_id}/stream` with a null chat ID.

- [x] T047 [Phase 12] [Chat Stream Service] Implement stream request service
  - Files: `frontend/src/services/chatStreamService.ts`
  - Action: Call `POST /api/chat/{chat_id}/stream` with `Accept: text/event-stream` and JSON body containing `query`, optional model fields, and `attached_files` file IDs.
  - Expected output: Service reads `ReadableStream` chunks with `TextDecoder`.
  - Validation: Source contains no call to nonexistent `/api/chat/stream`.

- [x] T048 [Phase 12] [Chat Stream Service] Implement stream callback application
  - Files: `frontend/src/services/chatStreamService.ts`, `frontend/src/hooks/useChatSessions.ts`
  - Action: Wire parser events to token append, thinking step update, source replacement, completion, and error state callbacks.
  - Expected output: UI updates progressively as events arrive.
  - Validation: Token events append without buffering the full answer.

- [x] T049 [P] [Phase 12] [Chat Stream Service] Add abort support
  - Files: `frontend/src/services/chatStreamService.ts`, `frontend/src/hooks/useChatStream.ts`
  - Action: Use `AbortController` for cancellation and cleanup on tab/session changes or user stop action.
  - Expected output: Aborted streams mark assistant message `cancelled` locally.
  - Validation: Abort does not show a fake backend rollback message.

- [x] T050 [Phase 12] [Chat Stream Service] Add chat stream hook
  - Files: `frontend/src/hooks/useChatStream.ts`
  - Action: Orchestrate send flow: validate text, upload files, create backend chat if needed, append user message, create assistant placeholder, stream, and cleanup.
  - Expected output: One hook owns send and retry lifecycle for the Chat workspace.
  - Validation: Upload failures prevent stream start and preserve input for retry.

## Phase 13: Input Bar

- [x] T051 [Phase 13] [Input Bar] Create sticky input bar component
  - Files: `frontend/src/components/chat/InputBar.tsx`, `frontend/src/components/chat/InputBar.css`
  - Action: Add Attach, Audio File, Tools, Model selector, textarea, and circular Send button.
  - Expected output: Input bar remains sticky at the bottom of Chat workspace.
  - Validation: Send button is disabled for empty trimmed text.

- [x] T052 [P] [Phase 13] [Input Bar] Implement keyboard behavior
  - Files: `frontend/src/components/chat/InputBar.tsx`
  - Action: Enter sends, Shift+Enter inserts newline, and composition text is not prematurely submitted.
  - Expected output: Keyboard send behavior matches the spec.
  - Validation: Manual or component test covers Enter and Shift+Enter.

- [x] T053 [P] [Phase 13] [Input Bar] Implement textarea autosize
  - Files: `frontend/src/components/chat/InputBar.tsx`, `frontend/src/components/chat/InputBar.css`
  - Action: Expand textarea up to 200px max height, then enable internal scrolling.
  - Expected output: Long prompts remain usable without breaking layout.
  - Validation: Textarea max height is capped at 200px.

- [x] T054 [Phase 13] [Input Bar] Wire input bar to send hook and attachments
  - Files: `frontend/src/components/chat/ChatWorkspace.tsx`, `frontend/src/components/chat/InputBar.tsx`
  - Action: Connect input text, selected files, send disabled state, upload state, and retry state.
  - Expected output: Sending calls the full upload/create-chat/stream flow.
  - Validation: Attachment-only send remains disabled unless text is non-empty.

## Phase 14: Message List

- [x] T055 [Phase 14] [Message List] Create chat workspace component
  - Files: `frontend/src/components/chat/ChatWorkspace.tsx`, `frontend/src/components/chat/ChatWorkspace.css`
  - Action: Compose message list, empty state, scroll region, and input bar.
  - Expected output: Chat tab displays conversation content centered with max-width constraints.
  - Validation: Empty state appears for a new chat with no messages.

- [x] T056 [P] [Phase 14] [Message List] Create message list component
  - Files: `frontend/src/components/chat/MessageList.tsx`, `frontend/src/components/chat/MessageList.css`
  - Action: Render user and assistant messages in order with stable keys and auto-scroll during streaming.
  - Expected output: New tokens remain visible without layout jank.
  - Validation: Auto-scroll does not steal position when user has intentionally scrolled up.

## Phase 15: User Message Card

- [x] T057 [Phase 15] [User Message Card] Create user message card
  - Files: `frontend/src/components/chat/UserMessageCard.tsx`, `frontend/src/components/chat/UserMessageCard.css`
  - Action: Render avatar, timestamp, text, uploaded attachment chips, and failed upload/send state when applicable.
  - Expected output: User messages clearly show sent text and backend file references.
  - Validation: Chips display `filename` and never expose local file paths.

## Phase 16: Assistant Message Card

- [x] T058 [Phase 16] [Assistant Message Card] Create assistant message card
  - Files: `frontend/src/components/chat/AssistantMessageCard.tsx`, `frontend/src/components/chat/AssistantMessageCard.css`
  - Action: Render logo header, thinking card slot, markdown response, stream cursor, source chips, and error state.
  - Expected output: Assistant card supports streaming, complete, failed, and cancelled states.
  - Validation: A stream `error` event keeps partial text visible and marks the message failed.

- [x] T059 [P] [Phase 16] [Assistant Message Card] Add assistant hover actions
  - Files: `frontend/src/components/chat/AssistantActions.tsx`, `frontend/src/components/chat/AssistantMessageCard.css`
  - Action: Add Copy, Regenerate, Expand, Export, Like, and Dislike ghost buttons as UI affordances.
  - Expected output: Actions fade in on hover/focus without implementing deferred backend workflows.
  - Validation: Buttons have accessible labels and unavailable actions do not call fake endpoints.

## Phase 17: Thinking Card

- [x] T060 [Phase 17] [Thinking Card] Create thinking card component
  - Files: `frontend/src/components/chat/ThinkingCard.tsx`, `frontend/src/components/chat/ThinkingCard.css`
  - Action: Render ordered thinking steps from backend events with received, complete, and failed states.
  - Expected output: Thinking steps are visible above assistant response while streaming.
  - Validation: Steps use event `type`, `content`, and `timestamp` from the backend payload.

- [x] T061 [P] [Phase 17] [Thinking Card] Add expand and collapse behavior
  - Files: `frontend/src/components/chat/ThinkingCard.tsx`
  - Action: Auto-expand while streaming, auto-collapse 2 seconds after success, and support manual toggle.
  - Expected output: User can inspect thinking steps after completion.
  - Validation: Auto-collapse does not run after a failed stream unless explicitly intended by UI copy.

## Phase 18: Markdown Renderer

- [x] T062 [Phase 18] [Markdown Renderer] Create markdown renderer wrapper
  - Files: `frontend/src/components/markdown/MarkdownRenderer.tsx`, `frontend/src/components/markdown/MarkdownRenderer.css`
  - Action: Render markdown with custom mappings for headings, bold, lists, links, tables, inline code, and code blocks.
  - Expected output: Assistant content renders with the Phase 4 design system.
  - Validation: Raw HTML is not rendered unless sanitization is explicitly approved.

- [x] T063 [P] [Phase 18] [Markdown Renderer] Add markdown failure fallback
  - Files: `frontend/src/components/markdown/MarkdownRenderer.tsx`
  - Action: Catch render issues and display safe plain text fallback.
  - Expected output: Bad markdown does not blank the assistant response.
  - Validation: Fallback does not use `dangerouslySetInnerHTML`.

## Phase 19: Code Block Copy Button

- [x] T064 [Phase 19] [Code Block Copy Button] Create code block component
  - Files: `frontend/src/components/markdown/CodeBlock.tsx`, `frontend/src/components/markdown/CodeBlock.css`
  - Action: Render dark code blocks with optional language label and copy button.
  - Expected output: Code snippets are readable and copyable.
  - Validation: Copy success and copy failure states are visible and accessible.

## Phase 20: Source Chips

- [x] T065 [Phase 20] [Source Chips] Create source chips component
  - Files: `frontend/src/components/chat/SourceChips.tsx`, `frontend/src/components/chat/SourceChips.css`
  - Action: Render source filename, file-type icon, relevance score if useful, and excerpt tooltip/label.
  - Expected output: Sources from backend `sources` event appear below assistant messages.
  - Validation: Component uses backend fields `file_id`, `filename`, `file_type`, `chunk_index`, `score`, and `excerpt`.

- [x] T066 [P] [Phase 20] [Source Chips] Add visible limit behavior
  - Files: `frontend/src/components/chat/SourceChips.tsx`
  - Action: Show up to 3 source chips and a `+N more` chip for remaining sources.
  - Expected output: Long source lists remain compact.
  - Validation: `+N more` count matches hidden source count.

## Phase 21: Status Service

- [x] T067 [Phase 21] [Status Service] Implement health status service
  - Files: `frontend/src/services/statusService.ts`
  - Action: Fetch `GET /health`, parse `status`, `version`, `database`, `qdrant`, and `ollama`, and map failures to `Unavailable`.
  - Expected output: Service returns a `ConnectionStatus` without fake fields.
  - Validation: Missing OCR, GPU, provider, and RAG enabled fields map to `Unknown` or `Unavailable`.

- [x] T068 [P] [Phase 21] [Status Service] Add connection status hook
  - Files: `frontend/src/hooks/useConnectionStatus.ts`
  - Action: Load status on app start, expose refresh, cache last check time, and surface loading/disconnected states.
  - Expected output: Header status can render current backend health.
  - Validation: Network failure sets `state: 'disconnected'` and does not throw into React render.

## Phase 22: Status Badge And Menu

- [x] T069 [Phase 22] [Status Badge And Menu] Create compact status badge
  - Files: `frontend/src/components/status/ConnectionStatusBadge.tsx`, `frontend/src/components/status/ConnectionStatusBadge.css`
  - Action: Render connected, degraded, disconnected, and loading states with text and dot indicator.
  - Expected output: Users can understand backend status at a glance.
  - Validation: Status is communicated with text, not color alone.

- [x] T070 [P] [Phase 22] [Status Badge And Menu] Create expanded status menu
  - Files: `frontend/src/components/status/ConnectionStatusMenu.tsx`, `frontend/src/components/status/ConnectionStatusMenu.css`
  - Action: Show backend version, database, Qdrant, Ollama, model, provider, RAG label, OCR, GPU, and troubleshooting hints.
  - Expected output: Missing fields display `Unknown` or `Unavailable`, not fake readiness.
  - Validation: Menu never displays fake `RAG Enabled`, fake model names, fake OCR Ready, or fake GPU Available.

## Phase 23: Error States And Retry Behavior

- [x] T071 [Phase 23] [Error States] Create reusable inline error component
  - Files: `frontend/src/components/ui/InlineError.tsx`, `frontend/src/components/ui/InlineError.css`
  - Action: Render friendly error text, optional retry button, and optional dismiss/remove action.
  - Expected output: Upload, stream, and status errors share consistent UI.
  - Validation: Component does not render raw backend stack traces.

- [x] T072 [Phase 23] [Retry Behavior] Implement retry for pre-stream failures
  - Files: `frontend/src/hooks/useChatStream.ts`, `frontend/src/components/chat/InputBar.tsx`
  - Action: Allow user-triggered retry when upload, chat creation, or stream open fails before tokens start.
  - Expected output: Retry reuses preserved input and valid uploaded references.
  - Validation: No automatic retry occurs after tokens have started.

- [x] T073 [Phase 23] [Retry Behavior] Implement failed attachment recovery
  - Files: `frontend/src/hooks/useAttachments.ts`, `frontend/src/components/chat/AttachmentTray.tsx`
  - Action: Allow failed files to be retried or removed before send proceeds.
  - Expected output: Users can resolve partial upload failure without losing text.
  - Validation: Failed file IDs are never included in `attached_files`.

## Phase 24: Reduced Motion And Accessibility

- [x] T074 [Phase 24] [Reduced Motion] Add reduced-motion hook
  - Files: `frontend/src/hooks/useReducedMotion.ts`
  - Action: Wrap `matchMedia('(prefers-reduced-motion: reduce)')` and expose a boolean to components.
  - Expected output: JS-controlled motion can follow OS preference.
  - Validation: Hook updates when the media query changes.

- [x] T075 [Phase 24] [Accessibility] Audit interactive labels and keyboard paths
  - Files: `frontend/src/components/**/*.tsx`
  - Action: Ensure buttons, tabs, status menu, source chips, copy controls, file remove controls, and retry controls have accessible names and keyboard access.
  - Expected output: Core UI is operable without a mouse.
  - Validation: Manual keyboard pass reaches all primary controls in logical order.

- [x] T076 [Phase 24] [Accessibility] Verify color-independent states
  - Files: `frontend/src/components/status/ConnectionStatusBadge.tsx`, `frontend/src/components/chat/*.tsx`, `frontend/src/components/ui/InlineError.tsx`
  - Action: Add text labels or icons so status, errors, active tab, and active chat are not color-only.
  - Expected output: State remains understandable for color-blind users.
  - Validation: Removing color in browser dev tools still leaves state text or shape cues.

## Phase 25: Tests

- [x] T077 [Phase 25] [Tests] Add test setup if absent
  - Files: `frontend/src/test/setup.ts`, `frontend/vitest.config.ts`, `frontend/package.json`
  - Action: Configure the selected frontend test runner and DOM test environment.
  - Expected output: `npm test` can run frontend unit/component tests.
  - Validation: A smoke test passes.

- [x] T078 [P] [Phase 25] [Tests] Test upload service
  - Files: `frontend/src/services/fileUploadService.test.ts`
  - Action: Cover endpoint selection, FormData field name, success mapping, unsupported type, payload error, and partial failure handling.
  - Expected output: Upload contract is protected by tests.
  - Validation: Test assertions verify one file per request.

- [x] T079 [P] [Phase 25] [Tests] Test status service
  - Files: `frontend/src/services/statusService.test.ts`
  - Action: Cover ok, degraded, network failure, non-2xx, Qdrant collection missing, and missing optional fields.
  - Expected output: Status never fabricates unavailable backend fields.
  - Validation: Tests assert model, provider, OCR, GPU, and RAG fallback labels.

- [x] T080 [P] [Phase 25] [Tests] Test local chat sessions hook
  - Files: `frontend/src/hooks/useChatSessions.test.ts`
  - Action: Cover session creation, active selection, title generation, message append, token append, source set, failure, and search filtering.
  - Expected output: Local chat state behavior is deterministic.
  - Validation: Search updates after debounce and sessions remain local-only.

- [x] T081 [P] [Phase 25] [Tests] Test chat stream hook flow
  - Files: `frontend/src/hooks/useChatStream.test.ts`
  - Action: Mock upload, chat creation, and stream callbacks to verify send order and failure handling.
  - Expected output: Send flow matches upload -> create chat -> stream.
  - Validation: Test fails if stream starts before uploads finish.

- [x] T082 [P] [Phase 25] [Tests] Test input bar behavior
  - Files: `frontend/src/components/chat/InputBar.test.tsx`
  - Action: Cover disabled empty send, Enter send, Shift+Enter newline, upload disabled state, and attachment-only blocked state.
  - Expected output: Input rules match Phase 4 scope.
  - Validation: Attachment-only send does not call submit.

- [x] T083 [P] [Phase 25] [Tests] Test thinking and assistant cards
  - Files: `frontend/src/components/chat/ThinkingCard.test.tsx`, `frontend/src/components/chat/AssistantMessageCard.test.tsx`
  - Action: Cover thinking step rendering, auto-collapse, stream cursor, error state, partial text, and source rendering.
  - Expected output: Streaming visual states are tested.
  - Validation: Error event keeps partial text visible.

- [x] T084 [P] [Phase 25] [Tests] Test markdown and code copy
  - Files: `frontend/src/components/markdown/MarkdownRenderer.test.tsx`, `frontend/src/components/markdown/CodeBlock.test.tsx`
  - Action: Cover headings, bold, lists, tables, inline code, fenced code, copy success, and copy failure.
  - Expected output: Markdown rendering and code copy are stable.
  - Validation: Tests confirm no unsafe raw HTML rendering.

- [x] T085 [P] [Phase 25] [Tests] Test tab and placeholder navigation
  - Files: `frontend/src/components/tabs/WorkspaceTabs.test.tsx`, `frontend/src/components/tabs/PlaceholderView.test.tsx`
  - Action: Cover active tab changes and placeholder content for Documents, OCR, Analysis, and Tools.
  - Expected output: Non-Chat tabs remain placeholders.
  - Validation: Tests assert placeholder copy and no backend calls.

- [x] T086 [P] [Phase 25] [Tests] Test status badge and menu
  - Files: `frontend/src/components/status/ConnectionStatusBadge.test.tsx`, `frontend/src/components/status/ConnectionStatusMenu.test.tsx`
  - Action: Cover loading, connected, degraded, disconnected, Unknown, and Unavailable rendering.
  - Expected output: Status UI reflects real contract limits.
  - Validation: Tests fail if fake RAG/model/OCR/GPU readiness text appears.

## Phase 26: Manual Quickstart Validation

- [x] T087 [Phase 26] [Manual Quickstart Validation] Execute quickstart checks
  - Files: `specs/004-frontend-core-ui/quickstart.md`
  - Action: Run the manual validation guide for install, backend, frontend, streaming, upload-before-send, sources, status, tabs, reduced motion, tests, and no fake data.
  - Expected output: Manual validation notes list pass/fail for each quickstart section.
  - Validation: Any failure is documented before final polish.

## Phase 27: Final Polish

- [x] T088 [Phase 27] [Final Polish] Run frontend quality commands once
  - Files: `frontend/package.json`
  - Action: Run the configured frontend lint, test, and build commands once after implementation.
  - Expected output: Quality commands complete or report exact errors.
  - Validation: If the same command fails twice with the same error, stop and report instead of looping.

- [x] T089 [Phase 27] [Final Polish] Verify no fake backend data is shown
  - Files: `frontend/src/services/statusService.ts`, `frontend/src/services/chatStreamService.ts`, `frontend/src/services/fileUploadService.ts`, `frontend/src/components/status/ConnectionStatusMenu.tsx`
  - Action: Inspect UI and service code for fake successful status, fake model/provider/RAG/OCR/GPU values, fake upload success, and fake stream events.
  - Expected output: Missing backend data renders as `Unknown`, `Unavailable`, degraded, or disconnected.
  - Validation: Search results contain no hardcoded fake success labels for missing backend fields.

- [x] T090 [Phase 27] [Final Polish] Verify Phase 4 exclusions
  - Files: `frontend/src/`, `frontend/app.py`, `frontend/utils/api_client.py`
  - Action: Confirm implementation has no Streamlit changes, no Python frontend client usage, no backend-persisted sidebar history, and no functional non-Chat workflows.
  - Expected output: Phase 4 remains focused on React core UI and verified backend integration.
  - Validation: Final diff shows React frontend files only, except approved config/package files.

## Dependency Order

- Phase 1 must complete before dependency or implementation work.
- Phase 2 must complete before React source files rely on package scripts or config.
- Phase 3 must complete before visual components are polished.
- Phases 4 through 8 establish shell, navigation, types, and local state.
- Phases 9 through 12 implement attachment upload and streaming integration.
- Phases 13 through 24 build UI surfaces, status, errors, and accessibility.
- Phase 25 tests should be added alongside or immediately after the related implementation tasks.
- Phases 26 and 27 validate the completed implementation.

## Parallel Opportunities

- `[P]` tasks can run in parallel when they touch different files and their phase prerequisites are complete.
- Parser, upload service, status service, and pure UI components can be implemented independently after types exist.
- Component tests can be written in parallel with their corresponding components once test setup exists.

## Blocked Tasks Requiring User Approval

- T004 may block browser-based React streaming if backend CORS does not allow the React dev-server origin.
- No backend implementation task is included; backend CORS/config changes require explicit user approval.
- The historical `/api/chat/stream` mismatch is not a backend task because the frontend can use the verified `POST /api/chats` plus `POST /api/chat/{chat_id}/stream` flow.

## Task Count

- Total tasks: 90
