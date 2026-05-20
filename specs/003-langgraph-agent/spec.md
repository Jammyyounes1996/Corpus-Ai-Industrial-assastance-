# Feature Specification: LangGraph Agent

**Feature Branch**: `004-langgraph-agent`
**Created**: 2026-05-20
**Status**: Draft
**Input**: User description: "read PLAN.md file and creat a specification for the phase 3 LangGraph Agent"

## Clarifications

### Session 2026-05-20

- Q: What timeout duration should be used for external service calls, and how many retries should be attempted before declaring failure?
  → A: 15 second timeout, 2 retries with exponential backoff (total 60s max)
- Q: What is the maximum number of conversation turns before summarization is triggered, and how should older messages be summarized?
  → A: 50 turns max, summarize to 2 sentence overview per 20 older turns
- Q: When multiple sources contain similar or duplicate information, how should citations be presented and ordered?
  → A: Order by similarity score, but merge duplicates from same file into single citation
- Q: How should the system handle incomplete responses when the SSE stream is interrupted by the user (page close, disconnect)?
  → A: Best-effort approach: show whatever streamed before disconnect; partial messages are persisted
- Q: What categories of content should be blocked for harmful queries, and what specific message should be displayed?
  → A: Use LLM's built-in safety guardrails; accept its determinations without additional filtering. The system displays whatever refusal message the model generates.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chat Query with RAG (Priority: P1)

Industrial engineers ask natural language questions about equipment manuals, audio recordings, and images. The system retrieves relevant context from ingested knowledge base, streams its reasoning process, and generates accurate answers with source citations.

**Why this priority**: This is the core value proposition of the assistant. Without working chat with retrieval, users cannot access their ingested industrial knowledge.

**Independent Test**: An engineer uploads a PDF equipment manual, then asks "What is the recommended maintenance interval for the bearings?" The system returns a correct answer with thinking steps visible and the PDF cited as a source.

**Acceptance Scenarios**:

1. **Given** a PDF equipment manual has been ingested and indexed, **When** the user asks a question about bearing maintenance, **Then** the system retrieves relevant passages from the PDF and returns accurate maintenance information with source citations.
2. **Given** an audio transcript has been chunked and stored, **When** the user asks about technician notes from a recording, **Then** the system searches audio transcript chunks and returns relevant information.
3. **Given** an image has been OCR'd and stored, **When** the user attaches an image and asks about equipment details, **Then** the system retrieves OCR text and incorporates it into the answer.
4. **Given** multiple file types contain relevant information, **When** the user asks a broad question, **Then** the system retrieves from PDFs, audio transcripts, and OCR results and synthesizes a comprehensive answer.

---

### User Story 2 - Multi-Turn Conversation Context (Priority: P1)

Industrial engineers engage in back-and-forth conversations to refine their understanding. The system maintains full conversation history and references previous exchanges when answering follow-up questions.

**Why this priority**: Complex industrial troubleshooting often requires iterative questioning. Without conversation memory, users must restate context on each turn, severely limiting usefulness.

**Independent Test**: An engineer asks about pump specifications, receives an answer, then follows up with "What about the flow rate?" without restating context. The system understands the follow-up refers to the pump mentioned earlier and provides the flow rate information.

**Acceptance Scenarios**:

1. **Given** the user previously asked about a specific pump model, **When** the user asks a follow-up question without repeating the model name, **Then** the system correctly interprets the question in the context of the previous conversation.
2. **Given** a 10-turn conversation has occurred, **When** the user asks a new question, **Then** the system maintains all relevant context from the conversation.
3. **Given** the user switches between discussing different equipment, **When** a question is asked, **Then** the system correctly tracks which equipment is being discussed in the current context.

---

### User Story 3 - Streaming Thinking Steps (Priority: P1)

Users see real-time feedback as the system processes their query. Each reasoning step appears progressively with status indicators, creating trust in the system's internal process.

**Why this priority**: Without visible thinking, the system is a black box. Users cannot distinguish between "thinking" and "stuck," leading to frustration and lack of trust.

**Independent Test**: A user asks a question and watches a thinking card appear with steps appearing one by one: "Analyzing your query..." → "Reading PDF documents..." → "Searching memory (RAG)..." → "Analyzing information..." → "Generating answer..." Each step shows an in-progress spinner that changes to a checkmark when complete.

**Acceptance Scenarios**:

1. **Given** the user asks a question, **When** processing begins, **Then** a thinking card appears with the first step "Analyzing your query..." showing an in-progress status.
2. **Given** a step is executing, **When** the step completes, **Then** the status changes from spinner to green checkmark and the next step appears.
3. **Given** an error occurs during retrieval, **When** the retrieval step fails, **Then** the thinking step shows a failure status and the system provides an explanation to the user.
4. **Given** all steps complete, **When** the final answer begins streaming, **Then** the thinking card collapses automatically after 2 seconds.

---

### User Story 4 - Source Citation and Verification (Priority: P1)

Users receive answers with clear source citations, enabling them to verify information accuracy and navigate to original documents.

**Why this priority**: Industrial applications require high trust. Engineers need to verify that AI answers are grounded in actual documentation, not hallucinations.

**Independent Test**: A user asks a question about pump specifications. The answer includes a "Sources" section with clickable chips showing "pump_manual.pdf [pages 12-14]" and other relevant files. Clicking a source opens the document to the relevant section.

**Acceptance Scenarios**:

1. **Given** the answer is based on PDF content, **When** the answer is displayed, **Then** clickable source chips appear showing the PDF filename and relevant page/chunk information.
2. **Given** multiple documents contain relevant information, **When** the answer draws from multiple sources, **Then** all relevant sources are listed with chips.
3. **Given** more than 3 sources are relevant, **When** sources are displayed, **Then** the first 3 show as chips and a "+N more" chip indicates additional sources.
4. **Given** a user clicks a source chip, **When** the chip is clicked, **Then** the original document opens and navigates to the relevant section.

---

### Edge Cases

- What happens when no relevant information is found in the knowledge base? The system should inform the user that it couldn't find relevant information and suggest they upload relevant documents.

- What happens when external retrieval services (GroundX, Qdrant) are unavailable? The system should use a 15-second timeout per call with 2 retries using exponential backoff (total 60s max). If retries are exhausted, the system shows a clear error message in the thinking steps and prompts user to check connection status.
- What happens when the conversation exceeds memory limits? The system should summarize the 20 oldest conversation turns (to 2 sentences per turn) to maintain context within acceptable limits once 50 turns are reached.
- What happens when multiple retrieved chunks from the same file have similar content? The system should merge duplicate citations from same file into single citation ordered by highest similarity score.
- What happens if user interrupts or disconnects during a streaming response? The system should use a best-effort approach: show whatever content streamed before the disconnect and persist partial messages as completed assistant messages.
- What happens when the query contains malicious or harmful content? The system should rely on the LLM's built-in safety guardrails and display whatever refusal message the model generates, without additional content filtering.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST analyze user queries to determine intent (PDF-only, audio-only, image-only, or hybrid).
- **FR-002**: System MUST retrieve relevant content from GroundX for PDF documents based on query analysis.
- **FR-003**: System MUST perform hybrid search over Qdrant vector store for audio transcripts and PDF chunks.
- **FR-004**: System MUST perform OCR on attached images using Gemma4 vision model.
- **FR-005**: System MUST synthesize retrieved context from multiple sources (PDFs, audio, images) into a unified context.
- **FR-006**: System MUST generate answers using the configured LLM (Gemma4 by default, with alternatives for Gemini/Grok).
- **FR-007**: System MUST stream thinking steps via Server-Sent Events (SSE) as each node in the agent graph executes.
- **FR-008**: System MUST stream generated answer tokens via SSE as they are produced by the LLM.
- **FR-009**: System MUST maintain conversation history across multiple message turns, including all previous messages and retrieved context.
- **FR-010**: System MUST persist chat sessions and messages to SQLite database for recovery and history.
- **FR-011**: System MUST provide source citations for all retrieved content used in generating answers.
- **FR-012**: System MUST handle multi-file queries where relevant information exists across PDFs, audio transcripts, and OCR results.
- **FR-013**: System MUST route queries based on detected intent (router node determines which retrieval paths to follow).
- **FR-014**: System MUST support streaming responses where tokens appear progressively as they are generated.
- **FR-015**: System MUST emit a final "done" event to signal SSE stream completion to clients.
- **FR-016**: System MUST validate chat session IDs and create new sessions when null or invalid IDs are provided.
- **FR-017**: System MUST support attaching files to queries for context-specific retrieval.
- **FR-018**: System MUST handle cases where no relevant information is found and provide helpful guidance to users.
- **FR-019**: System MUST gracefully handle failures in external services (GroundX, Qdrant, Ollama) using 15-second timeout per call with 2 retries with exponential backoff (total 60s max), and report errors in thinking steps.
- **FR-020**: System MUST support conversation context limits with summarization of older turns when needed. Maximum 50 turns before summarization triggers, summarizing 20 oldest turns to 2 sentence overview per turn.

### Key Entities

- **Chat**: Represents a conversation session containing multiple message exchanges. Has unique ID, title (auto-generated from first message), model provider used, and timestamps.
- **Message**: Represents a single message in a conversation. Contains role (user/assistant), content, thinking steps, retrieved context, and created timestamp.
- **ThinkingStep**: Represents a single step in the agent's reasoning process. Contains step description, status (pending/in_progress/completed/failed), node name, and duration in milliseconds.
- **Source**: Represents a document or chunk that contributed to the answer. Contains file ID, filename, file type, chunk index, similarity score, and excerpt text.
- **AgentState**: Represents the complete state of the agent during execution. Contains user input, conversation memory, intermediate results, and final output.
- **RetrievalResult**: Represents content retrieved from a source (GroundX, Qdrant, OCR). Contains source type, content, metadata, and relevance score.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users receive first thinking step within 3 seconds of submitting a query.
- **SC-002**: Full answers (including all thinking steps) complete within 30 seconds for typical queries over ingested content.
- **SC-003**: 95% of answers correctly cite the source documents from which information was retrieved.
- **SC-004**: Multi-turn conversations correctly maintain context across at least 10 consecutive message exchanges.
- **SC-005**: Source citations include accurate chunk references with similarity scores for 90% of cited sources. Citations are ordered by similarity score, with duplicate chunks from same file merged into single citation.
- **SC-006**: The system handles queries over empty knowledge base gracefully within 2 seconds (no timeout).
- **SC-007**: Streaming token latency averages less than 200ms between tokens during answer generation.
- **SC-008**: 90% of users report that thinking steps help them understand how the system reached its answer (measured via feedback).
- **SC-009**: Cross-source queries (combining PDF, audio, and image information) successfully synthesize information in at least 80% of test cases.
- **SC-010**: Failed retrieval nodes report clear error messages in thinking steps without causing system crashes.

## Assumptions

- Phase 2 (Ingestion Pipeline) is complete, providing functional PDF ingestion, audio transcription, and image OCR with content stored in GroundX, Qdrant, and SQLite.
- Ollama server is running with Gemma4 model available for generation.
- Qdrant is running and contains indexed chunks from audio transcripts and PDFs.
- GroundX API is configured and has indexed PDF documents.
- SQLite database contains chat session and message tables from Phase 1 foundation.
- Frontend SSE client (httpx-sse) is available to consume thinking step and token events.
- Users have ingested at least one document type (PDF, audio, or image) before testing chat functionality.
- Network latency between backend and external services is under 500ms for 95% of requests.
- System runs in single-user mode (no multi-tenant isolation requirements).
