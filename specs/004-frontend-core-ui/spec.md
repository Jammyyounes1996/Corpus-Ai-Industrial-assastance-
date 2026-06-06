# Feature Specification: Frontend Core UI

**Feature Branch**: `specs/004-frontend-core-ui`  
**Created**: 2026-05-31  
**Status**: Draft  
**Input**: User description: "Phase 4 — Frontend Core UI: Pixel-perfect Claude-inspired interface with working chat, sidebar, tab navigation, thinking steps, and SSE streaming"

## Clarifications

### Session 2026-05-31

- Q: Which frontend framework should Phase 4 use given the conflict between the project React stack and Streamlit assumptions? → A: React frontend in `frontend/src`, using browser-native streaming.
- Q: For the non-Chat workspace tabs in Phase 4 (`Documents`, `OCR`, `Analysis`, `Tools`), should this phase implement functional screens or only navigable placeholder views? → A: Placeholder views only for non-Chat tabs.
- Q: Which streaming request pattern should Phase 4 use for chat messages with session and attachment context? → A: `fetch` POST streaming to `/api/chat/stream`, with the request body including message, session, and attachment references.
- Q: For Phase 4 chat history/sidebar sessions, should chats be persisted through backend APIs or handled as local frontend state only? → A: Local frontend state only.
- Q: For Phase 4 file attachments, should the frontend upload files to the backend before sending the chat message, or only show local attachment previews and pass references if already available? → A: Upload attachments before chat send.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Send a Chat Message and Receive a Streamed Response (Priority: P1)

An industrial engineer opens the application and sees the main workspace with a sidebar on the left and the Chat tab active. They type a question about their equipment into the input bar at the bottom and press Send. The application streams the AI's response in real time: a "Thinking" card appears above the response showing each processing step (analyzing query, reading documents, searching memory, generating answer) with animated status indicators. Once complete, the AI response renders with formatted markdown — blue headings, orange-accented bold text, styled code blocks, and source chips below the response citing the documents used.

**Why this priority**: The chat experience is the primary interaction model for the entire application. Without a working chat with streaming, no other feature delivers value.

**Independent Test**: Can be fully tested by launching the frontend, typing a message, and verifying the thinking steps animate progressively and the response streams token-by-token with proper markdown rendering.

**Acceptance Scenarios**:

1. **Given** the application is loaded with the Chat tab active, **When** the user types a question and clicks Send (or presses Enter), **Then** a `fetch` POST streaming request is opened to `/api/chat/stream`, thinking steps appear progressively with animated spinners transitioning to checkmarks, and the response streams token-by-token into a styled card.
2. **Given** the AI response includes markdown content (headings, bold, code blocks, tables, bullet lists), **When** the response finishes streaming, **Then** all markdown renders with the custom design system colors (blue headings, orange bold, dark code blocks with copy button, custom bullet markers).
3. **Given** the AI response includes source references, **When** the response completes, **Then** source chips appear below the response showing filenames with type icons, and a "+N more" chip if more than 3 sources exist.
4. **Given** a message is being streamed, **When** the user observes the response area, **Then** a blinking cursor appears at the end of the streaming text.

---

### User Story 2 - Navigate and Manage Chats via the Sidebar (Priority: P1)

An industrial engineer uses the sidebar to manage their conversations within the current frontend session. They see the application logo and title at the top, a "New Chat" button, a search field, and a list of locally tracked chats with timestamps. They click "New Chat" to start a fresh conversation, search through existing local chats by typing in the search field, and click a previous local chat to reload its in-memory history. The sidebar also shows Projects, Knowledge Bases, and Tools sections for quick access to related features.

**Why this priority**: The sidebar is the primary navigation and organization mechanism. Users cannot efficiently use the application without it.

**Independent Test**: Can be tested by creating multiple chats, verifying they appear in the sidebar with timestamps, searching/filtering chats, and switching between them.

**Acceptance Scenarios**:

1. **Given** the application is loaded, **When** the user views the sidebar, **Then** they see the animated starburst logo, "Industrial AI Assistant" title, "New Chat" button, search field, and sections for Chats, Projects, Knowledge Bases, and Tools.
2. **Given** the user has previous conversations, **When** they view the Chats section, **Then** each chat shows a truncated title and a relative timestamp ("2m ago", "Yesterday", "3d ago"), with the active chat highlighted with an orange left border.
3. **Given** multiple chats exist, **When** the user types in the search field, **Then** the chat list filters in real time (debounced at 200ms) to show only matching chats.
4. **Given** the user clicks "New Chat", **When** the action completes, **Then** a new chat session is created and the Chat tab displays an empty conversation ready for input.

---

### User Story 3 - View Connection Status and Model Information (Priority: P2)

An industrial engineer glances at the top-right corner of the workspace to check whether the AI model is connected. They see a status indicator showing a green dot for connected (or red for disconnected), the model name, provider, and whether RAG is enabled. They can click or expand this indicator to see additional details like GPU status and Qdrant availability.

**Why this priority**: Connection status gives users confidence the system is ready and helps them troubleshoot issues. It is important but not blocking for core chat functionality.

**Independent Test**: Can be tested by checking the status indicator reflects the actual backend connection state, and toggling Ollama on/off to verify status updates.

**Acceptance Scenarios**:

1. **Given** the backend and Ollama are running, **When** the application loads, **Then** the status indicator shows a green dot with "Connected to local model" and displays the model name, provider, and "RAG Enabled".
2. **Given** the backend is unreachable, **When** the application attempts to connect, **Then** the status indicator shows a red dot with "Disconnected" and provides troubleshooting context.
3. **Given** the status indicator is visible, **When** the user clicks the dropdown arrow, **Then** an expanded view shows GPU status, Qdrant connection status, and OCR readiness.

---

### User Story 4 - Attach Files to Chat Messages (Priority: P2)

An industrial engineer wants to ask about a specific document or image. They click the "Attach" button in the input bar to open a file picker, select a PDF, image, or audio file, and see a preview chip appear above the input bar. They can attach multiple files and remove any by clicking the X on its chip. When they send the message, the frontend uploads the attached files first, then includes the returned attachment references with the query for the AI to process.

**Why this priority**: File attachment is central to the industrial use case (manuals, images, audio), but the basic chat must work first.

**Independent Test**: Can be tested by attaching files of each type, verifying preview chips appear, removing an attachment, and sending a message with attachments.

**Acceptance Scenarios**:

1. **Given** the input bar is visible, **When** the user clicks "+ Attach", **Then** a file picker opens allowing selection of PDF, image, or audio files.
2. **Given** the user selects one or more files, **When** the files are attached, **Then** preview chips appear above the input bar showing filenames (with thumbnails for images), each with an X button to remove.
3. **Given** files are attached and a message is typed, **When** the user clicks Send, **Then** the files upload successfully before the chat streaming request is opened, the message is sent with the returned file references included, and the AI processes the attachments as part of its response.

---

### User Story 5 - Switch Between Workspace Tabs (Priority: P2)

An industrial engineer uses the top tab bar to navigate between different workspace views: Chat, Documents, OCR, Analysis, and Tools. Each tab has an icon and label. The active tab is highlighted with an orange underline, and switching tabs smoothly transitions the content area.

**Why this priority**: Tab navigation provides access to the full feature set, but the Chat tab alone delivers the core value.

**Independent Test**: Can be tested by clicking each tab and verifying the underline moves, the content area transitions, and the correct view loads.

**Acceptance Scenarios**:

1. **Given** the application is loaded, **When** the user views the top bar, **Then** five tabs are visible (Chat, Documents, OCR, Analysis, Tools) with Lucide icons and the Chat tab active by default.
2. **Given** the Chat tab is active, **When** the user clicks another tab, **Then** the underline smoothly slides to the new tab (250ms ease-out), the content area fades to a polished placeholder view for that tab (200ms), and the tab text/icon colors update.
3. **Given** the user is on any tab, **When** they hover over an inactive tab, **Then** a subtle background appears with a smooth 200ms transition.

---

### User Story 6 - Experience Polished Animations and Interactions (Priority: P3)

An industrial engineer interacts with the application and experiences consistent, premium-feeling animations: the starburst icon rotates and breathes subtly, hover effects provide tactile feedback on buttons and cards, thinking step transitions are smooth, and the streaming cursor blinks at the end of incoming text. If the user has enabled reduced motion in their OS settings, all animations are minimized.

**Why this priority**: Animations elevate the perceived quality of the application but are cosmetic enhancements on top of working functionality.

**Independent Test**: Can be tested by observing animations during normal use and verifying they respect the OS reduced-motion preference.

**Acceptance Scenarios**:

1. **Given** the application is loaded, **When** the user observes the starburst icon, **Then** it slowly rotates (8s cycle) and subtly scales (breathing effect, 3s cycle).
2. **Given** the user hovers over interactive elements, **When** hovering on buttons, cards, or sidebar items, **Then** appropriate hover effects appear (scale 1.02, shadow lift, background fade) within 150-200ms.
3. **Given** the OS has reduced-motion enabled, **When** the application loads, **Then** all animations are effectively disabled (duration near 0ms) per the `prefers-reduced-motion` media query.

---

### Edge Cases

- What happens when the streaming request drops mid-stream? The UI should display a graceful error message and offer to retry the last message.
- What happens when the chat list is empty? The sidebar Chats section shows "No conversations yet" placeholder text.
- What happens when the user sends an empty message? The Send button is disabled (gray) when the textarea is empty, preventing submission.
- What happens when a very long message is typed? The input bar textarea expands up to 200px max-height, then becomes scrollable internally.
- What happens when the AI response contains very long content? The message container scrolls vertically with smooth scrolling behavior.
- What happens when the user presses Enter vs Shift+Enter? Enter sends the message; Shift+Enter inserts a newline in the textarea.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The application MUST render a sidebar (280px wide) containing the logo header, "New Chat" button, search field, and collapsible sections for Chats, Projects, Knowledge Bases, Tools, and a Settings footer.
- **FR-002**: The application MUST render a top tab bar with five tabs (Chat, Documents, OCR, Analysis, Tools), each with a Lucide icon, supporting active state highlighting with an orange underline.
- **FR-002a**: The Documents, OCR, Analysis, and Tools tabs MUST render navigable placeholder views only in Phase 4; fully functional non-Chat workflows are out of scope for this phase.
- **FR-003**: The application MUST render a status indicator in the top-right corner showing connection state (green/red dot), model name, provider, and RAG status, with a dropdown for additional details.
- **FR-004**: The Chat tab MUST display a scrollable message container (max-width 900px, centered) showing user messages and AI response cards.
- **FR-005**: User messages MUST render with an avatar (32px), content area with border and padding, and a right-aligned timestamp.
- **FR-006**: The application MUST render a "Thinking" card above AI responses showing LangGraph processing steps with animated status indicators (spinner for in-progress, checkmark for completed, empty circle for pending).
- **FR-006a**: The application MUST send chat streaming requests with `fetch` POST to `/api/chat/stream`, including message text, chat/session identifiers, and attachment references in the JSON request body, then read the streamed response incrementally.
- **FR-007**: The Thinking card MUST auto-expand during streaming, auto-collapse 2 seconds after the final step completes, and allow manual toggle by the user.
- **FR-008**: AI response cards MUST render markdown with custom styling: blue headings (#4A6FA5), orange bold text, monospace inline code with cream background, dark code blocks with copy button, custom orange bullet markers, and clean-bordered tables.
- **FR-009**: Source chips MUST appear below AI responses showing filenames with file-type icons, limited to 3 visible with a "+N more" chip for additional sources.
- **FR-010**: The input bar MUST be sticky at the bottom of the main area, containing: Attach button, Audio File button, Tools dropdown, Model selector, expandable textarea, and a circular Send button.
- **FR-011**: The Send button MUST be disabled when the textarea is empty and enabled with a glow effect when text is present. Enter sends the message; Shift+Enter inserts a newline.
- **FR-012**: The application MUST consume streamed events from the backend (`thinking_step`, `token`, `sources`, `done`) and render them progressively in real time.
- **FR-013**: Attached files MUST display as preview chips above the input bar (horizontal scrollable), each with a filename and X button to remove. Image attachments show a 40x40 thumbnail.
- **FR-013a**: When attachments are present, the application MUST upload files to the backend before opening the `/api/chat/stream` request and MUST include only returned attachment references in the chat streaming request body.
- **FR-014**: The sidebar chat list MUST support live search filtering (debounced 200ms) and display relative timestamps for each chat entry.
- **FR-014a**: Phase 4 chat sessions and sidebar history MUST be stored in local frontend state only; backend-persisted chat history is out of scope for this phase.
- **FR-015**: AI response cards MUST show action buttons on hover (Copy, Regenerate, Expand, Export, Like, Dislike) as 32x32 ghost-style icons that fade in over 200ms.
- **FR-016**: The application MUST apply the complete design system including the defined color palette, typography (Inter font family), spacing tokens, border radii, and shadow values.
- **FR-017**: The animated starburst icon MUST display a continuous slow rotation (8-second cycle) and a subtle breathing effect (scale pulse over 3 seconds), used consistently in the logo, AI message headers, and thinking card headers.
- **FR-018**: All animations MUST respect the user's OS-level reduced-motion accessibility preference, effectively disabling motion when the user has indicated they prefer reduced motion.
- **FR-019**: The sidebar "New Chat" button MUST create a new chat session and navigate to the Chat tab with an empty conversation.
- **FR-020**: The sidebar chat entries MUST show an active state (orange left border, active background color) for the currently selected chat.

### Key Entities

- **Chat Session**: Represents a conversation between the user and the AI, containing a title (auto-generated from first message), timestamp, optional project association, and an ordered list of messages.
- **Message**: A single exchange unit within a chat — either from the user or the AI. User messages contain text and optional file attachments. AI messages contain rendered markdown content, thinking steps, and source references.
- **Thinking Step**: A status entry representing a LangGraph processing node, with a description string, status (pending/in-progress/completed), and optional duration.
- **Source Reference**: A citation chip linking an AI response to the document chunk that informed it, containing filename, file type, and relevance score.
- **Attached File**: A file reference included with a user message, showing filename, type (PDF/audio/image), and optional thumbnail preview.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can send a message and see the full streamed response (thinking steps + answer + sources) within a single, uninterrupted interaction flow.
- **SC-002**: The visual appearance of the interface achieves greater than 90% similarity to the Claude-inspired design reference, as judged by side-by-side comparison.
- **SC-003**: Thinking step animations transition smoothly (spinner to checkmark) with no visible jank or layout shifts during streaming.
- **SC-004**: All interactive elements (buttons, tabs, sidebar items, cards) respond to hover within 200ms with visible feedback.
- **SC-005**: Users can create a new chat, send a message, and receive a response within 3 interactions (click New Chat, type message, press Send).
- **SC-006**: The sidebar chat search filters results as the user types, with visible updates within 300ms of the last keystroke.
- **SC-007**: Tab switching transitions complete within 500ms including content fade and underline slide.
- **SC-008**: The application renders correctly on desktop screens 1280px wide and above, with the sidebar and main content area properly laid out.
- **SC-009**: Users with OS-level reduced motion enabled experience no distracting animations while retaining full functionality.
- **SC-010**: Markdown content in AI responses renders all supported elements (headings, bold, code, tables, lists, links) with the correct design system colors and styles.

## Assumptions

- The backend API (FastAPI) is already functional with `/api/chat/stream` delivering streamed `thinking_step`, `token`, `sources`, and `done` events as specified in the API contract.
- React is the UI framework, implemented under `frontend/src` with component-level styling/CSS for the Claude-inspired design system.
- The application targets desktop browsers only (1280px+ width); mobile/responsive layout is out of scope.
- The Inter font family is available via system fonts or a web font import; fallback to system sans-serif fonts is acceptable.
- Lucide icons are used as inline SVGs, not as an external icon font dependency.
- Backend-persisted chat CRUD endpoints are not required for Phase 4 sidebar chat management; chat/session history is local frontend state only.
- Dark mode is not included in this phase — it is deferred to Phase 6 (Advanced Features).
- The Settings modal functionality is deferred to Phase 6; the sidebar Settings footer link is present but opens a placeholder or minimal view.
- Documents, OCR, Analysis, and Tools tab functionality beyond polished placeholder views is deferred to later phases.
- File upload/ingestion endpoints are already functional from Phase 2; the frontend only needs to call them and display results.
- Browser-native `fetch` POST streaming to `/api/chat/stream` is used for chat streaming from the React application; Python `httpx`/`httpx-sse` clients and `EventSource`-only GET streaming are out of scope for the frontend.
