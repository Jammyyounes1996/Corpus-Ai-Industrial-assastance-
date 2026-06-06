# Feature Specification: Remaining Workspace Tabs

**Feature Branch**: `specs/005-remaining-tabs`  
**Created**: 2026-06-06  
**Status**: Draft  
**Input**: User description: "Phase 5 Remaining Tabs — Documents, OCR, Analysis, Tools tabs all functional per PLAN.md sections 4.6–4.9"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse and Manage Knowledge Base Documents (Priority: P1)

An industrial engineer opens the Documents tab to see all files they have uploaded to the system. They can view files as a grid of cards, filter by type (PDF, Audio, Image), sort by date or name, and upload new documents. They can also delete documents they no longer need.

**Why this priority**: The Documents tab is the gateway to the knowledge base. Without it, users have no way to see what content the AI assistant has access to, making the entire system feel like a black box.

**Independent Test**: Can be fully tested by navigating to the Documents tab, verifying the file grid loads from the existing `/api/files` endpoint, uploading a new file, and deleting an existing file. Delivers a visible inventory of all ingested content.

**Acceptance Scenarios**:

1. **Given** files have been ingested, **When** the user navigates to the Documents tab, **Then** they see a 3-column grid of document cards showing filename, file type icon, size, upload date, and indexing status badge ("Indexed" in green or "Processing" in orange)
2. **Given** the Documents tab is open, **When** the user clicks "+ Upload Document", **Then** a file picker opens accepting PDF, audio, and image files, and upon selection the file is uploaded and appears in the grid with a "Processing" badge
3. **Given** a document card is visible, **When** the user hovers over it, **Then** a delete icon appears in the top-right corner
4. **Given** the user clicks the delete icon on a document, **When** a confirmation dialog appears and the user confirms, **Then** the file is removed from the grid, disk, database, and vector store
5. **Given** the Documents tab shows multiple file types, **When** the user selects "PDF" from the type filter, **Then** only PDF documents are displayed
6. **Given** no files have been uploaded, **When** the user navigates to the Documents tab, **Then** they see an empty state with an illustration and the message "No documents yet. Upload your first PDF, audio, or image."

---

### User Story 2 - View and Act on OCR Image History (Priority: P2)

An industrial engineer opens the OCR tab to browse a gallery of all images previously processed by the system's OCR capability. Each image shows a thumbnail preview. Clicking an image creates a new chat session with that image pre-attached and a starter prompt, enabling quick follow-up questions about the image content.

**Why this priority**: OCR results are generated as a byproduct of image ingestion. Providing a dedicated gallery view with click-to-chat makes previously analyzed images discoverable and actionable, directly supporting the daily usage workflow described in the plan.

**Independent Test**: Can be tested by navigating to the OCR tab after at least one image has been ingested, verifying the gallery grid renders thumbnails, and clicking an image to confirm it opens a new chat with the image attached.

**Acceptance Scenarios**:

1. **Given** images have been ingested and OCR'd, **When** the user navigates to the OCR tab, **Then** they see a 4-column grid of image thumbnails (200x200, object-fit: cover) with filename overlays
2. **Given** an OCR thumbnail is visible, **When** the user hovers over it, **Then** an "Open in Chat" overlay appears along with a tooltip showing a preview of the extracted text
3. **Given** the user clicks an OCR thumbnail, **When** the action completes, **Then** a new chat session is created with the image pre-attached and the first message pre-filled as "Tell me about this image", and the view navigates to the Chat tab

> **Accepted Limitation (US2-3):** OCR tab creates chat sessions with filename reference in message text. Formal file attachment requires a real browser `File` object and is deferred to a future phase.
4. **Given** no images have been ingested, **When** the user navigates to the OCR tab, **Then** they see an empty state with a message like "No images analyzed yet. Upload an image to get started."

---

### User Story 3 - Inspect LangGraph Execution Traces (Priority: P3)

An industrial engineer wants to understand how the AI arrived at its answer. They navigate to the Analysis tab to see the full execution trace of the last conversation turn — which LangGraph nodes ran, what context was retrieved, and the raw model reasoning output.

**Why this priority**: Transparency into the AI's reasoning builds trust. For industrial applications where incorrect answers can have safety implications, seeing the retrieval trace and reasoning steps is critical for validating response quality.

**Independent Test**: Can be tested by sending a chat message that triggers retrieval, then navigating to the Analysis tab to verify all three sections (execution trace, retrieved context, model thinking) display real data from the last turn.

**Acceptance Scenarios**:

1. **Given** the user has had at least one conversation turn, **When** they navigate to the Analysis tab, **Then** they see three vertically stacked sections: "LangGraph Execution Trace", "Retrieved Context", and "Model Reasoning Output"
2. **Given** the Execution Trace section is visible, **When** the last turn involved multiple nodes, **Then** a vertical timeline shows each node with its name, status badge (completed/failed/skipped), execution time in milliseconds, and collapsible input/output summaries
3. **Given** the Retrieved Context section is visible, **When** context chunks were used in the last answer, **Then** each chunk card shows the source filename, chunk index, similarity score (0-1), and expandable chunk text (collapsed to 2 lines by default)
4. **Given** the Model Reasoning section is visible, **When** the model produced reasoning output, **Then** the raw output is rendered in a monospace block with token count and generation time displayed
5. **Given** no conversations have occurred, **When** the user navigates to the Analysis tab, **Then** they see a message indicating no trace data is available yet

---

### User Story 4 - Run RAGAS Evaluation on Chat Responses (Priority: P3)

An industrial engineer wants to measure the quality of the AI's retrieval and response. They navigate to the Tools tab, select the RAGAS Evaluator view, and run an evaluation on the last chat message. The system computes two RAG quality metrics (Faithfulness and Answer Relevancy) and displays them as score cards with gauge visualizations. Context Precision and Context Recall are omitted because they require ground-truth reference answers not available in this system.

**Why this priority**: RAGAS evaluation is a differentiating feature for this industrial AI assistant, enabling objective measurement of retrieval quality — critical for validating the system's reliability with industrial documentation.

**Independent Test**: Can be tested by sending a chat message, navigating to the Tools tab, clicking "Run Evaluation on Last Chat", and verifying two metric cards (Faithfulness, Answer Relevancy) display scores.

**Acceptance Scenarios**:

1. **Given** the user navigates to the Tools tab, **When** the tab loads, **Then** they see a toggle at the top to switch between "RAGAS Evaluator" and "Audio Transcriber" views
2. **Given** the RAGAS Evaluator view is active, **When** the user clicks "Run Evaluation on Last Chat", **Then** the system evaluates the last chat turn and displays two metric cards: Faithfulness and Answer Relevancy, each showing a score (0-1), a gauge visualization, and a brief explanation
3. **Given** an evaluation completes, **When** the results are displayed, **Then** a history table below the metrics shows past evaluations with timestamps, chat reference, and scores
4. **Given** the RAGAS Evaluator view is active, **When** the user opens the model selector, **Then** the system scans the local Ollama instance and displays all available models as a dropdown — the selected model is used as the LLM judge for the next evaluation run
5. **Given** no chat messages exist, **When** the user tries to run an evaluation, **Then** a message indicates no chat data is available for evaluation

---

### User Story 5 - Browse Audio Transcriptions (Priority: P3)

An industrial engineer wants to review transcriptions of audio recordings they've uploaded. They navigate to the Tools tab, switch to the Audio Transcriber view, and see a list of all transcribed audio files with expandable transcript text.

**Why this priority**: Audio transcriptions are generated during ingestion but have no dedicated browsing interface. This view makes transcripts discoverable and reusable.

**Independent Test**: Can be tested by ingesting an audio file, navigating to the Tools tab, switching to the Audio Transcriber view, and verifying the transcript is displayed with playback controls.

**Acceptance Scenarios**:

1. **Given** audio files have been transcribed, **When** the user selects the "Audio Transcriber" view in the Tools tab, **Then** they see a list of all uploaded audio files showing filename, duration, and upload date
2. **Given** an audio file item is visible, **When** the user expands it, **Then** they see the full transcript text (scrollable) and a "Copy transcript" button
3. **Given** the user clicks "Copy transcript", **When** the action completes, **Then** the transcript text is copied to the clipboard and a confirmation is shown
4. **Given** no audio files have been transcribed, **When** the user opens the Audio Transcriber view, **Then** an empty state message is displayed

---

### Edge Cases

- What happens when a file upload fails mid-transfer? The upload button re-enables and an error toast is displayed with the specific failure reason.
- What happens when the backend is unreachable while loading the Documents or OCR tab? A connection error message is shown inline with a "Retry" button.
- What happens when RAGAS evaluation takes a long time (>30 seconds)? A loading state with thinking-style step indicators is shown to keep the user informed.
- What happens when the user navigates away from the Analysis tab before data loads? Data fetching is cancelled to prevent stale state.
- What happens when a document's indexing status changes while viewing the Documents tab? The status badge updates on the next poll or manual refresh.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display all ingested files in a filterable, sortable 3-column grid in the Documents tab
- **FR-002**: System MUST allow file upload from the Documents tab using the existing ingestion endpoints (`/api/ingest/pdf`, `/api/ingest/audio`, `/api/ingest/image`)
- **FR-003**: System MUST support file deletion from the Documents tab with a confirmation dialog, using the existing `DELETE /api/files/{file_id}` endpoint
- **FR-004**: System MUST display an empty state view in each tab when no relevant data exists
- **FR-005**: System MUST render a 4-column image thumbnail gallery in the OCR tab using image data from the backend
- **FR-006**: System MUST create a new chat session with a pre-attached image and starter prompt when the user clicks an OCR thumbnail
- **FR-007**: System MUST display a vertical timeline of LangGraph execution nodes in the Analysis tab, with node name, status, and execution time
- **FR-008**: System MUST display retrieved context chunks in the Analysis tab with source, score, and expandable text
- **FR-009**: System MUST display model reasoning output in a monospace block in the Analysis tab
- **FR-010**: System MUST provide a RAGAS Evaluator view in the Tools tab that computes and displays Faithfulness and Answer Relevancy (Context Precision and Context Recall require ground-truth data not available in this system)
- **FR-011**: System MUST provide an Audio Transcriber view in the Tools tab listing all transcribed audio files with expandable transcripts
- **FR-012**: System MUST maintain visual consistency with the established Claude-inspired design system (warm palette, border radii, spacing, typography) across all new tabs
- **FR-013**: System MUST allow toggling between RAGAS Evaluator and Audio Transcriber sub-views within the Tools tab
- **FR-014**: System MUST provide filter controls in the Documents tab for file type (All / PDF / Audio / Image) and sort order (Date descending / Name A-Z / Size)
- **FR-015**: The RAGAS Evaluator MUST include a model selector that fetches available models from the local Ollama instance (`GET http://localhost:11434/api/tags`) and allows the user to switch the judge model before running evaluation. The selected model persists for the session.

### Key Entities

- **Document Card**: Represents a file in the knowledge base — shows name, type icon, size, upload date, and indexing status. Used in the Documents tab grid.
- **OCR Thumbnail**: Represents a previously OCR'd image — shows image preview, filename, and extracted text preview on hover. Used in the OCR gallery.
- **Execution Trace Node**: Represents a single LangGraph node execution — includes node name, status, duration, and collapsible input/output. Used in the Analysis tab timeline.
- **Context Chunk**: Represents a retrieved document chunk — includes source file, chunk index, similarity score, and chunk text. Used in the Analysis tab.
- **Evaluation Result**: Represents a RAGAS evaluation — includes two metric scores (Faithfulness, Answer Relevancy), model_used (which Ollama model served as the judge — enables comparison of scores across different models for the same message), timestamp, and associated chat reference. Used in the Tools tab.
- **Audio Transcript**: Represents a transcribed audio file — includes filename, duration, language, and full transcript text. Used in the Tools tab.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can find and identify any uploaded document within 5 seconds of opening the Documents tab
- **SC-002**: Users can upload a new file from the Documents tab and see it appear in the grid within 3 seconds of upload completion
- **SC-003**: Users can delete a document with no more than 2 clicks (hover for delete icon + confirm)
- **SC-004**: Users can navigate from an OCR image thumbnail to a new chat with that image in under 2 seconds
- **SC-005**: Users can view the full execution trace of the last conversation turn within 3 seconds of opening the Analysis tab
- **SC-006**: Users can initiate and view a RAGAS evaluation with results displayed within 60 seconds for a typical conversation turn
- **SC-007**: All four tabs render with visual consistency matching the established design system (colors, typography, spacing, card styles)
- **SC-008**: Users can switch between any two tabs and see content render within 500 milliseconds
- **SC-009**: Each tab displays an appropriate empty state when no data is available, guiding users on how to populate it

## Assumptions

- The existing backend endpoints (`/api/files`, `DELETE /api/files/{file_id}`, `/api/ingest/*`) are fully functional and will be consumed by the Documents tab without modification
- OCR results and image paths are stored in the database and accessible through backend endpoints (may require a new OCR history endpoint)
- LangGraph execution trace data (node names, timing, status) is available via an API endpoint or stored in the chat message metadata (the `thinking_steps` and `retrieved_context` JSON fields in the `messages` table)
- The RAGAS evaluation library is installed and a backend evaluation endpoint will be created as part of this phase
- Audio transcript data is accessible through the existing file metadata enrichment in the `/api/files` endpoint
- The frontend is built with React/TypeScript/Vite (not Streamlit as originally planned in PLAN.md) — all tab implementations will use React components
- The existing `WorkspaceContent` component and `PlaceholderView` pattern will be replaced with real tab implementations
- Backend routes for OCR history (`/api/ocr/history`), evaluation (`/api/evaluate`), and analysis trace data need to be created as part of this feature
