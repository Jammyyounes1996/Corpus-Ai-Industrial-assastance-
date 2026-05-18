# Tasks: Foundation & Setup

**Input**: Design documents from `specs/001-foundation-setup/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/api.md

**Tests**: Tests are OPTIONAL for Phase 1 - focus on getting infrastructure running first.

**Organization**: Tasks organized by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, etc.)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create backend directory structure with __init__.py files
- [ ] T002 [P] Create frontend directory structure with __init__.py files
- [ ] T003 [P] Create tests directory structure with __init__.py files
- [ ] T004 [P] Create scripts directory
- [ ] T005 [P] Create data directory with subdirectories (uploads, audio, images)
- [ ] T006 Create .gitkeep file in data/uploads/
- [ ] T007 Create .gitkeep file in data/audio/
- [ ] T008 Create .gitkeep file in data/images/

**Checkpoint**: Project structure created - ready for configuration files

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core configuration files that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T009 Create environment.yml with Python 3.12 and dependencies list
- [ ] T010 [P] Create requirements.txt with all pinned dependencies
- [ ] T011 [P] Create .env.example with all environment variables including: WHISPER_DEVICE=auto, WHISPER_COMPUTE_TYPE=auto, SECRET_KEY with comment, MAX_PDF_SIZE_MB=100, MAX_AUDIO_SIZE_MB=100, MAX_IMAGE_SIZE_MB=25
- [ ] T012 [P] Create .gitignore with Python, environment, data, and IDE patterns
- [ ] T013 [P] Create docker-compose.yml with Qdrant v1.12.0 service
- [ ] T014 [P] Create README.md with project title and installation placeholder
- [ ] T015 Create backend/config/__init__.py
- [ ] T016 Create backend/utils/__init__.py
- [ ] T017 [P] Create backend/config/settings.py with pydantic-settings class
- [ ] T018 [P] Create backend/utils/logging.py with loguru configuration
- [ ] T019 Create backend/database/__init__.py
- [ ] T020 Create backend/database/migrations/__init__.py
- [ ] T021 Create backend/database/migrations/versions/__init__.py
- [ ] T022 Create backend/database/database.py with async engine and session factory
- [ ] T023 Create backend/database/models/__init__.py
- [ ] T024 [P] Create Project model in backend/database/models.py
- [ ] T025 [P] Create Chat model in backend/database/models.py
- [ ] T026 [P] Create Message model in backend/database/models.py
- [ ] T027 [P] Create File model in backend/database/models.py
- [ ] T028 [P] Create OCRResult model in backend/database/models.py
- [ ] T029 [P] Create Transcript model in backend/database/models.py
- [ ] T030 [P] Create AppSettings model in backend/database/models.py
- [ ] T031 [P] Create EvaluationResult model in backend/database/models.py
- [ ] T032 Add all 9 Index definitions to backend/database/models.py
- [ ] T033 Add foreign key constraints to backend/database/models.py
- [ ] T035 Create backend/main.py with FastAPI app instance
- [ ] T036 Add CORS middleware to backend/main.py for localhost:8501
- [ ] T037 Add GET /health endpoint to backend/main.py
- [ ] T038 Add startup/shutdown events to backend/main.py
- [ ] T039 Add exception handlers to backend/main.py
- [ ] T096 Create backend/schemas/health.py with HealthResponse Pydantic model (status, database, qdrant, ollama, version fields)
- [ ] T040 Create frontend/__init__.py
- [ ] T041 Create frontend/components/__init__.py
- [ ] T042 Create frontend/styles/__init__.py
- [ ] T043 Create frontend/state/__init__.py
- [ ] T044 Create frontend/utils/__init__.py
- [ ] T045 [P] Create frontend/styles/load_css.py with CSS injection helper
- [ ] T046 [P] Create frontend/styles/main.css with skeleton CSS and design tokens
- [ ] T047 Create frontend/state/session.py with session state helpers
- [ ] T048 Create frontend/utils/api_client.py with HTTP client skeleton
- [ ] T049 Create frontend/app.py with basic page layout (sidebar + tabs)
- [ ] T050 [P] Create scripts/init_db.py that creates SQLite database with all tables and default AppSettings row
- [ ] T051 [P] Create scripts/setup_Qdrant_collection.py that creates industrial_assistant collection
- [ ] T052 [P] Create scripts/generate_secret_key.py that outputs Fernet key
- [ ] T053 [P] Create scripts/verify_environment.py that checks all services

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Developer Environment Setup (Priority: P1) 🎯 MVP

**Goal**: Developer can set up a complete development environment from scratch by cloning the repository and following documented installation steps

**Independent Test**: A new developer can clone the repository, follow installation instructions, and verify success by running health checks on both backend and frontend services

### Implementation for User Story 1

- [ ] T054 Verify environment.yml includes all dependencies from plan.md
- [ ] T055 Verify requirements.txt has all dependencies pinned to exact versions
- [ ] T056 Verify .env.example documents all required environment variables
- [ ] T057 Verify .gitignore excludes environment files, data directories, and Python cache
- [ ] T058 Verify docker-compose.yml has correct Qdrant service configuration
- [ ] T059 Verify README.md provides clear installation instructions

**Checkpoint**: Developer can follow installation steps to set up complete environment

---

## Phase 4: User Story 2 - Backend Health Check (Priority: P1) 🎯 MVP

**Goal**: Developers and monitoring systems can verify that the backend service is operational by calling a health check endpoint

**Independent Test**: A developer can send a GET request to /health and receive a JSON response indicating status of all required services

### Implementation for User Story 2

- [ ] T060 Verify /health endpoint returns correct JSON format with status field
- [ ] T061 Verify health check includes database connection status
- [ ] T062 Verify health check includes Qdrant connection status
- [ ] T063 Verify health check includes Ollama connection status
- [ ] T064 Verify health endpoint returns HTTP 200 when all services available
- [ ] T065 Verify health endpoint handles service disconnection gracefully

**Checkpoint**: Health endpoint provides service status for all critical dependencies

---

## Phase 5: User Story 3 - Database Initialization (Priority: P1) 🎯 MVP

**Goal**: Developers can initialize the application database with all required tables, indexes, and constraints using a single command

**Independent Test**: A developer runs the init_db script and can verify the database file exists with all expected tables and proper foreign key relationships

### Implementation for User Story 3

- [ ] T066 Verify init_db script creates SQLite database at expected path
- [ ] T067 Verify all 8 tables are created: Project, Chat, Message, File, OCRResult, Transcript, AppSettings, EvaluationResult
- [ ] T068 Verify all required indexes are present for query optimization
- [ ] T069 Verify AppSettings singleton row (id=1) exists with default values
- [ ] T070 Verify foreign key constraints are properly defined

**Checkpoint**: Database is fully initialized and ready for application use

---

## Phase 6: User Story 4 - Vector Store Setup (Priority: P1) 🎯 MVP

**Goal**: Developers can initialize the vector store (Qdrant) with the required collection configuration using a single command

**Independent Test**: A developer runs the setup_Qdrant_collection script and can verify the collection exists with correct dimension settings

### Implementation for User Story 4

- [ ] T071 Verify setup_Qdrant_collection script creates "industrial_assistant" collection
- [ ] T072 Verify collection has dense vectors configured for 768 dimensions
- [ ] T073 Verify collection has sparse vector support enabled
- [ ] T074 Verify script handles existing collection gracefully
- [ ] T075 Verify script provides clear error messages on Qdrant connection failure

**Checkpoint**: Qdrant collection is properly configured for hybrid search

---

## Phase 7: User Story 5 - Configuration Management (Priority: P2)

**Goal**: Developers can configure the application using environment variables with a validated template

**Independent Test**: A developer can copy .env.example to .env, provide required values, and the application starts without configuration errors

### Implementation for User Story 5

- [ ] T076 Verify pydantic-settings loads all environment variables
- [ ] T077 Verify settings class validates configuration at startup
- [ ] T078 Verify missing required variables cause startup failure with clear error message
- [ ] T079 Verify invalid configuration values are rejected with helpful error messages
- [ ] T080 Verify settings module provides type-safe access to all configuration values

**Checkpoint**: Application configuration is type-safe and validated

---

## Phase 8: User Story 6 - Frontend Layout Structure (Priority: P2)

**Goal**: Developers have a working Streamlit frontend with the basic page layout (sidebar, tabs, and content areas)

**Independent Test**: A developer runs Streamlit and sees a complete page layout with a sidebar on the left and tab content on the right

### Implementation for User Story 6

- [ ] T081 Verify frontend/app.py displays sidebar on the left side of the screen
- [ ] T082 Verify frontend displays all tab placeholders
- [ ] T083 Verify tab navigation switches content correctly
- [ ] T084 Verify design tokens (colors, spacing, typography) are applied via main.css
- [ ] T085 Verify session state is properly initialized
- [ ] T086 Verify CSS is loaded via load_css.py helper function
- [ ] T087 Verify api_client.py skeleton provides HTTP client structure

**Checkpoint**: Frontend layout structure is ready for component development

---

## Phase 9: Validation

**Purpose**: Verify everything works and meets acceptance criteria

- [ ] T088 Run `python scripts/init_db.py` and verify industrial_ai.db created with all tables
- [ ] T089 Run `python scripts/setup_Qdrant_collection.py` and verify Qdrant collection created
- [ ] T090 Verify database is initialized and accessible before health checks
- [ ] T091 Verify uvicorn backend.main:app --reload starts successfully
- [ ] T092 Run `curl http://localhost:8000/health` and verify returns `{"status":"ok"}` with service statuses
- [ ] T093 Run `streamlit run frontend/app.py` and verify UI loads with sidebar + tabs
- [ ] T094 Run `python scripts/verify_environment.py` and verify all checks pass
- [ ] T095 Verify Docker Qdrant container is accessible at localhost:6333
- [ ] T096 Verify application cold start is under 10 seconds for both services

**Checkpoint**: All validation tests pass - foundation is complete and ready for feature development

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
- **Validation (Phase 9)**: Depends on all previous phases

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Foundational (Phase 2) - No dependencies on other user stories
- **User Story 2 (P1)**: Depends on Foundational (Phase 2) and backend/main.py from Phase 2
- **User Story 3 (P1)**: Depends on Foundational (Phase 2) - No dependencies on other stories
- **User Story 4 (P1)**: Depends on Foundational (Phase 2) - No dependencies on other stories
- **User Story 5 (P2)**: Depends on Foundational (Phase 2) - No dependencies on other stories
- **User Story 6 (P2)**: Depends on Foundational (Phase 2) - No dependencies on other stories

### Within Each User Story

- Implementation tasks must follow completion order as listed
- Verification tasks must complete after implementation

### Parallel Opportunities

- **Phase 1**: T002-T008 can run in parallel (different directories)
- **Phase 2**: Many tasks marked [P] can run in parallel (different configuration files)
- **Phase 2 Models**: T024-T031 can run in parallel (same file but different models)
- **Phase 2 Frontend**: T045-T048 can run in parallel (different files)
- **Phase 2 Scripts**: T050-T053 can run in parallel (different scripts)

---

## Parallel Example: Phase 2 Configuration Files

```bash
# Launch all configuration file tasks in parallel (different files, no dependencies):
Task: "Create requirements.txt with all pinned dependencies"
Task: "Create .env.example with all environment variables..."
Task: "Create .gitignore with Python, environment, data..."
Task: "Create docker-compose.yml with Qdrant v1.12.0 service"
Task: "Create README.md with project title..."
```

---

## Implementation Strategy

### MVP First (User Stories 1-4 Only - P1 Priority)

1. Complete Phase 1: Setup (Project structure)
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Developer Environment Setup)
4. Complete Phase 4: User Story 2 (Backend Health Check)
5. Complete Phase 5: User Story 3 (Database Initialization)
6. Complete Phase 6: User Story 4 (Vector Store Setup)
7. Complete Phase 9: Validation
8. **STOP and VALIDATE**: All P1 user stories and validation pass

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready for development
2. Add User Stories 1-4 (P1) → Test independently → Validate
3. Add User Stories 5-6 (P2) → Test independently → Validate
4. Each story adds infrastructure capability without breaking previous work

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Stories 1 & 2 (Environment Setup, Health Check)
   - Developer B: User Stories 3 & 4 (Database, Vector Store)
   - Developer C: User Stories 5 & 6 (Configuration, Frontend Layout)
3. Stories complete and integrate independently
4. Team completes Validation together

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- User Stories 1-4 are P1 (critical for MVP)
- User Stories 5-6 are P2 (important but can follow MVP)
- Tests are optional for Phase 1 - focus on infrastructure first
- Validation tasks require all services running (Docker, Ollama, backend, frontend)
- Database initialization (T088) must include AppSettings singleton row (id=1)
- Ollama model download is not part of Phase 1 tasks - assumes Ollama is already set up
