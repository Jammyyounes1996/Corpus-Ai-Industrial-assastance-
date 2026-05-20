# Tasks: LangGraph Agent

**Input**: Design documents from `specs/003-langgraph-agent/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/api.md

**Tests**: Tests are OPTIONAL for this feature - focus on getting LangGraph agent running first.

**Organization**: Tasks organized by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, etc.)
- Include exact file paths in descriptions

---

## Phase 1: Database Schema (Shared Foundation)

**Purpose**: Create Chat and Message tables with required indexes and migrations

- [ ] T001 [P] Create Chat SQLAlchemy model in backend/database/models.py with id, title, project_id (FK), model_provider, model_name, created_at, updated_at fields
- [ ] T002 [P] Create Message SQLAlchemy model in backend/database/models.py with id, chat_id (FK), role (enum: user/assistant), content (TEXT), thinking_steps (JSON), retrieved_context (JSON), attached_files (JSON), created_at fields
- [ ] T003 [P] Add Index(idx_chats_updated_at) on Chat.updated_at in DESC order for efficient listing
- [ ] T004 [P] Add Index(idx_chats_project_id) on Chat.project_id for project filtering queries
- [ ] T005 [P] Add Index(idx_messages_chat_id_created) on Message.chat_id and created_at for message retrieval
- [ ] T006 [P] Create Alembic migration for Chat and Message tables via alembic revision --autogenerate -m

**Checkpoint**: Database schema ready for chat and message persistence

---

## Phase 2: Agent Core (Shared Infrastructure)

**Purpose**: Implement LangGraph agent state, nodes, graph, and streaming infrastructure

**⚠️ CRITICAL**: All user stories depend on this phase being complete

- [ ] T007 [P] Create backend/core/agent/__init__.py file
- [ ] T008 [P] Create AgentState TypedDict in backend/core/agent/state.py with chat_id, user_message, attached_image_path, attached_files, messages, query_intent, groundx_results, qdrant_results, ocr_result, thinking_steps, final_answer, sources fields
- [ ] T009 [P] Implement router_node in backend/core/agent/nodes.py with query analysis logic to set query_intent (pdf_only/audio_only/image_only/general)
- [ ] T010 [P] Implement groundx_retrieve_node in backend/core/agent/nodes.py calling GroundX client and storing results in state
- [ ] T011 [P] Implement qdrant_retrieve_node in backend/core/agent/nodes.py calling Qdrant hybrid search and storing results in state
- [ ] T012 [P] Implement ocr_node in backend/core/agent/nodes.py calling Gemma4 vision for attached images and storing OCR result
- [ ] T013 [P] Implement context_synthesis_node in backend/core/agent/nodes.py combining retrieved context from all sources into unified context
- [ ] T014 [P] Implement answer_node in backend/core/agent/nodes.py calling LLM to generate final answer with sources
- [ ] T015 [P] Create LangGraph graph in backend/core/agent/graph.py with conditional edges based on query_intent
- [ ] T016 [P] Define LangChain tools in backend/core/agent/tools.py for retrievals (GroundX, Qdrant, OCR)
- [ ] T017 [P] Create SSE streaming helpers in backend/core/agent/streaming.py with ThinkingStep and Source event classes
- [ ] T018 [P] Implement RRF (Reciprocal Rank Fusion) in backend/core/retrieval/fusion.py with k=60 constant and score combination logic

**Checkpoint**: Agent infrastructure ready for all retrieval and generation

---

## Phase 3: API Routes (User Story 1 - Chat Query with RAG) (Priority: P1) 🎯 MVP

**Goal**: Industrial engineers can ask natural language questions and receive streamed answers with thinking steps.

**Independent Test**: An engineer uploads a PDF equipment manual, then asks "What is the recommended maintenance interval for bearings?" The system returns a correct answer with thinking steps visible and PDF cited as a source.

### Implementation for User Story 1

- [ ] T019 [US1] Create backend/api/routes/chat.py module with POST /api/chat/stream, GET /api/chats, GET /api/chat/{id}, DELETE /api/chat/{id} endpoints
- [ ] T020 [US1] Implement POST /api/chat/stream SSE endpoint accepting ChatRequest, yielding thinking_step, token, sources, and done events via SSE
- [ ] T021 [US1] Implement chat_id validation logic for new sessions (null/invalid) and existing sessions (valid UUID)
- [ ] T022 [US1] Implement GET /api/chats endpoint returning list of ChatSummary objects sorted by updated_at DESC
- [ ] T023 [US1] Implement GET /api/chat/{id} endpoint returning full chat with all messages in created_at ASC order
- [ ] T024 [US1] Implement DELETE /api/chat/{id} endpoint with cascading delete of messages and validation that chat exists
- [ ] T025 [US1] Add error handling for ValidationError (invalid chat_id), ChatNotFound (404), and internal AgentError with structured JSON responses
- [ ] T026 [US1] Configure CORS for frontend (http://localhost:8501) in chat.py router setup

**Checkpoint**: Chat API endpoints functional with SSE streaming

---

## Phase 4: User Story 2 - Multi-Turn Conversation Context (Priority: P1) 🎯 MVP

**Goal**: Engineers engage in back-and-forth conversations and the system maintains full context across turns.

**Independent Test**: An engineer asks about pump specifications, receives an answer, then follows up with "What about the flow rate?" without restating context. The system correctly interprets the follow-up and provides flow rate information.

### Implementation for User Story 2

- [ ] T027 [US2] Create create_chat function in backend/database/crud.py generating UUID for chat_id, auto-generating title from first message, setting model_provider/model_name, and persisting to database
- [ ] T028 [US2] Create create_message function in backend/database/crud.py storing role, content, thinking_steps (JSON), retrieved_context (JSON), attached_files (JSON), and created_at
- [ ] T029 [US2] Create get_chat_messages function in backend/database/crud.py retrieving all messages for a chat_id in chronological order (created_at ASC)
- [ ] T030 [US2] Create delete_chat function in backend/database/crud.py with transaction support cascading delete of all messages in the chat
- [ ] T031 [US2] Implement message history retrieval in answer_node by fetching last N messages from database when chat_id is provided
- [ ] T032 [US2] Implement conversation summarization in backend/core/agent/nodes.py for context_synthesis_node to check if 50-turn limit exceeded and summarize 20 oldest turns to 2 sentences per turn
- [ ] T033 [US2] Add conversation context loading in router_node to fetch existing messages when chat_id is provided and populate AgentState.messages field

**Checkpoint**: Multi-turn conversation with context memory and summarization functional

---

## Phase 5: User Story 3 - Streaming Thinking Steps (Priority: P1) 🎯 MVP

**Goal**: Users see real-time feedback as the system processes their query with progressive status indicators.

**Independent Test**: A user asks a question and watches a thinking card appear with steps appearing one by one. Each step shows an in-progress spinner that changes to a green checkmark when complete.

### Implementation for User Story 3

- [ ] T034 [US3] Define ThinkingStep Pydantic model in backend/schemas/chat.py with step, status (enum: pending/in_progress/completed/failed), node_name, and duration_ms fields
- [ ] T035 [US3] Implement thinking step emission in backend/core/agent/nodes.py yielding ThinkingStep events via astream_events with status transition timing
- [ ] T036 [US3] Define exact thinking step text mappings for each node in backend/core/agent/streaming.py: router_node→"Analyzing your query...", groundx_retrieve→"Reading PDF documents...", qdrant_retrieve→"Searching memory (RAG)...", ocr→"Running OCR on images...", context_synthesis→"Analyzing information...", answer→"Generating answer..."
- [ ] T037 [US3] Implement thinking step event format in backend/core/agent/streaming.py following SSE protocol (event: thinking_step with JSON payload)
- [ ] T038 [US3] Add duration tracking in backend/core/agent/nodes.py using time.perf_counter() to calculate execution time for each node
- [ ] T039 [US3] Implement status transition logic: pending→in_progress on node start, in_progress→completed on success, in_progress→failed on error

**Checkpoint**: Thinking steps streamed with accurate status, timing, and descriptions

---

## Phase 6: User Story 4 - Source Citation and Verification (Priority: P1) 🎯 MVP

**Goal**: Users receive answers with clear source citations enabling verification and navigation.

**Independent Test**: A user asks about pump specifications and the answer includes clickable source chips showing "pump_manual.pdf [pages 12-14]". Clicking a chip opens the document.

### Implementation for User Story 4

- [ ] T040 [US4] Define Source Pydantic model in backend/schemas/chat.py with file_id, filename, file_type (pdf/audio/image), chunk_index, similarity_score, and excerpt_text fields
- [ ] T041 [US4] Implement source extraction in answer_node from all retrieved results (groundx_results, qdrant_results, ocr_result) and populate sources list with similarity scores
- [ ] T042 [US4] Implement source citation ordering in answer_node sorting by similarity_score DESC (highest first)
- [ ] T043 [US4] Implement duplicate merging in answer_node: when multiple sources from same file_id exist, merge into single citation with highest similarity score
- [ ] T044 [US4] Emit sources event after token stream completes in backend/core/agent/nodes.py with sources list ordered and de-duplicated
- [ ] T045 [US4] Add "+N more" chip logic in backend/core/agent/nodes.py when sources list exceeds 3, showing first 3 with "+N more" indicator

**Checkpoint**: Source citations displayed accurately with similarity scores and deduplication

---

## Phase 7: CRUD Operations (Cross-Story Support)

**Purpose**: Database operations for chat and message persistence used by all user stories

- [ ] T046 [P] Create create_chat function in backend/database/crud.py generating UUID, setting title from first message (truncate to 255 chars), and persisting to database
- [ ] T047 [P] Create get_chat function in backend/database/crud.py retrieving Chat by id with all relationships loaded
- [ ] T048 [P] Create get_chats function in backend/database/crud.py returning list of chats with optional project_id, type, sort, and limit filters
- [ ] T049 [P] Create update_chat function in backend/database/crud.py updating updated_at timestamp and optionally title
- [ ] T050 [P] Create delete_chat function in backend/database/crud.py with transaction support cascading delete of all messages
- [ ] T051 [P] Create create_message function in backend/database/crud.py storing message with JSON serialization for thinking_steps, retrieved_context, attached_files
- [ ] T052 [P] Create get_messages function in backend/database/crud.py retrieving messages for a chat_id in created_at ASC order

**Checkpoint**: Complete CRUD operations for chat and message management

---

## Phase 8: Schemas (Request/Response Models)

**Purpose**: Pydantic models for chat API validation and serialization

- [ ] T053 [P] Create backend/schemas/chat.py module
- [ ] T054 [P] Create ChatRequest Pydantic model with chat_id (UUID|None), message (str, min 1 char), and attached_files (list[str], optional)
- [ ] T055 [P] Create ThinkingStep Pydantic model with step, status (enum), node_name (str), and duration_ms (float|None)
- [ ] T056 [P] Create Source Pydantic model with file_id, filename, file_type, chunk_index (int), similarity_score (float), and excerpt_text (str)
- [ ] T057 [P] Create ChatSummary Pydantic model for listing with id, title, model_provider, model_name, created_at, updated_at, message_count fields
- [ ] T058 [P] Create ChatDetail Pydantic model with id, title, model_provider, model_name, created_at, updated_at, and messages list
- [ ] T059 [P] Create ErrorResponse Pydantic model with error, message, and optional details dict

**Checkpoint**: All API contracts have Pydantic models for validation

---

## Phase 9: Integration & Testing

**Purpose**: Mount router, connect components, and verify end-to-end functionality

- [ ] T060 [P] Import and include chat router in backend/main.py
- [ ] T061 [P] Test POST /api/chat/stream with simple question and verify SSE stream yields thinking_step, token, sources, and done events
- [ ] T062 [P] Test GET /api/chats and verify list returns sessions sorted by updated_at DESC
- [ ] T063 [P] Test GET /api/chat/{id} and verify full conversation including messages and sources is returned
- [ ] T064 [P] Test DELETE /api/chat/{id} and verify cascading delete removes all messages
- [ ] T065 [P] Test chat_id validation with invalid UUID returns 404 ChatNotFound error
- [ ] T066 [P] Test multi-turn conversation by asking follow-up question and verifying context is maintained
- [ ] T067 [P] Test 50-turn summarization by creating conversation with 51 turns and verifying oldest 20 are summarized
- [ ] T068 [P] Test source citations with ingested PDF and verify correct file, chunk, and similarity score are returned
- [ ] T069 [P] Test external service timeout by simulating 16s GroundX delay and verifying 2 retries with backoff occur
- [ ] T070 [P] Test SC-006 - empty knowledge base by querying without any ingested documents and verify helpful response is returned within 2 seconds
- [ ] T071 [P] Test SC-007 - streaming token latency by measuring time between consecutive token events during answer generation and verify average stays under 200ms
- [ ] T072 [P] Test SC-009 - cross-source query success by asking questions requiring both GroundX (PDF) and Qdrant (audio) data and verify 80%+ success rate

**Checkpoint**: End-to-end agent chat flow working with streaming, context, and citations

---

## Dependencies & Execution Order

### Phase Dependencies

- **Database Schema (Phase 1)**: No dependencies - can start immediately
- **Agent Core (Phase 2)**: Depends on Database Schema - blocks user stories
- **API Routes (Phase 3)**: Depends on Agent Core and Schemas - US1 implementation
- **User Story 2 (Phase 4)**: Depends on Database Schema and Agent Core - independent of US1
- **User Story 3 (Phase 5)**: Depends on Agent Core and Schemas - independent of US1/US2
- **User Story 4 (Phase 6)**: Depends on Agent Core, Schemas, and retrieval nodes - independent of US1/US2/US3
- **CRUD Operations (Phase 7)**: Depends on Database Schema - shared by all
- **Schemas (Phase 8)**: Depends on nothing - can be done in parallel with Phase 1
- **Integration (Phase 9)**: Depends on all previous phases - final verification

### Parallel Opportunities

- **Phase 1**: T001, T002, T003-T005 can run in parallel (different tables/indexes, no dependencies)
- **Phase 2**: T007 can run in parallel with Phase 1 tables creation (but before migration)
- **Phase 2**: T009-T018 can run in parallel (different files/modules, no dependencies within agent core)
- **Phase 8**: T053-T009 can run in parallel (different Pydantic models, no dependencies)
- **Phase 4 & 6**: Can run in parallel after Agent Core is complete
- **User Stories**: Once Agent Core and Schemas are complete, US1, US2, US3, US4 can all proceed in parallel

### Sequential Dependencies Within Each Phase

- **Phase 1**: T001, T002 before T003-T005 (tables before indexes), T006 (migration after tables/indexes)
- **Phase 2**: T008 before T009 (state before nodes), T009-T014 before T015 (nodes before graph), graph before tools usage
- **Phase 3**: T020 depends on T019 (router) and T025 (validation), T021-T024 depend on T046-T050 (CRUD)
- **Phase 4**: T027-T030 can run in parallel, T031-T032 can run in parallel
- **Phase 5**: T034 depends on T008 (schema), T035-T039 depend on T008-T014 (nodes)
- **Phase 6**: T040-T045 depend on T006 (schema) and T014 (answer node with sources)
- **Phase 7**: T046-T052 can run in parallel, T050 depends on T002 (Message model)
- **Phase 9**: All tasks sequential after previous phases complete

---

## Parallel Example: Phase 2 Agent Core

```bash
# Launch all agent core tasks in parallel:
Task: "Create backend/core/agent/__init__.py"
Task: "Create AgentState TypedDict in backend/core/agent/state.py"
Task: "Implement router_node in backend/core/agent/nodes.py"
Task: "Implement groundx_retrieve_node in backend/core/agent/nodes.py"
Task: "Implement qdrant_retrieve_node in backend/core/agent/nodes.py"
Task: "Implement ocr_node in backend/core/agent/nodes.py"
Task: "Implement context_synthesis_node in backend/core/agent/nodes.py"
Task: "Implement answer_node in backend/core/agent/nodes.py"
Task: "Create LangGraph graph in backend/core/agent/graph.py"
Task: "Define LangChain tools in backend/core/agent/tools.py"
Task: "Create SSE streaming helpers in backend/core/agent/streaming.py"
Task: "Implement RRF fusion in backend/core/retrieval/fusion.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1-4 Only - All P1 Priority)

Since all 4 user stories have P1 priority and are foundational to the chat experience, implement them together:

1. Complete Phase 1: Database Schema
2. Complete Phase 2: Agent Core (shared by all stories)
3. Complete Phase 8: Schemas (needed by all API phases)
4. Implement User Stories 3, 6, 4 in parallel after core is ready:
   - Phase 3: API Routes (US1)
   - Phase 4: Multi-Turn Context (US2)
   - Phase 5: Streaming Thinking Steps (US3)
   - Phase 6: Source Citations (US4)
5. Complete Phase 7: CRUD Operations
6. Complete Phase 9: Integration & Testing
7. **STOP and VALIDATE**: All 4 user stories are fully functional with streaming, context, and citations

### Incremental Delivery

Each user story adds value incrementally:
- US1 adds basic chat with retrieval and answers
- US2 adds conversation memory for multi-turn troubleshooting
- US3 adds transparency through streaming thinking steps
- US4 adds trust through source citations

Stories complete and integrate without breaking previous stories.

### Parallel Team Strategy

With multiple developers:

1. Team completes Phase 1 & 8 (Database, Schemas) together
2. Once Phase 1 & 8 are done, Team works on Phase 2 (Agent Core) together
3. Once Agent Core is complete:
   - Developer A: US3 (Streaming Thinking Steps)
   - Developer B: US4 (Source Citations)
   - Developer C: US1 (API Routes) with US2 (CRUD) as support
4. Team completes Phase 9 (Integration) together
5. Stories complete and integrate seamlessly with shared agent infrastructure

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- User Stories 1-4 are all P1 (critical for MVP)
- Tests are optional for this phase - focus on infrastructure first
- Phase 2 Agent Core is critical foundation that all user stories depend on
- Conversation summarization triggers at 50 turns with 20-turn summary (2 sentences per turn)
- External services use 15s timeout with 2 retries and exponential backoff (60s max total)
- Source citations ordered by similarity score with duplicates from same file merged
- LLM built-in guardrails handle harmful content without additional filtering
- SSE streams use `thinking_step`, `token`, `sources`, and `done` events
- Chat and Message tables use JSON columns for complex data (thinking_steps, retrieved_context, attached_files)
