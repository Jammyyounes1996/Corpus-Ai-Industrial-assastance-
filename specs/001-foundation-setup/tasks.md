# Tasks: Foundation & Setup

**Input**: Design documents from `specs/001-foundation-setup/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Tests are OPTIONAL for Phase 1 - focus on getting infrastructure running first.

**Organization**: Tasks organized by Phase 1 deliverables from plan.md

## Format: `[ID] [P?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **Description**: Clear action with exact file path
- Each task is small enough for cheaper LLMs to complete

---

## Phase 1: Project Structure

**Purpose**: Create all folders and empty `__init__.py` files

- [ ] T001 Create backend directory structure with __init__.py files
- [ ] T002 [P] Create frontend directory structure with __init__.py files
- [ ] T003 [P] Create data directory with subdirectories (uploads, audio, images)
- [ ] T004 [P] Create tests directory structure with __init__.py files
- [ ] T005 [P] Create scripts directory
- [ ] T006 Create .gitkeep file in data/uploads/
- [ ] T007 Create .gitkeep file in data/audio/
- [ ] T008 Create .gitkeep file in data/images/

---

## Phase 2: Configuration Files

**Purpose**: Create all config files at repository root

- [ ] T009 Create environment.yml with Python 3.11 and dependencies list
- [ ] T010 Create requirements.txt with all pinned dependencies from plan.md Section 9.2
- [ ] T011 Create .env.example with all environment variables from plan.md Section 9.4
- [ ] T012 Create .gitignore with Python, environment, data, and IDE patterns
- [ ] T013 Create docker-compose.yml with Qdrant v1.12.0 service from plan.md Section 9.5
- [ ] T014 Create README.md with project title and installation placeholder

---

## Phase 3: Backend Configuration

**Purpose**: Backend settings, logging, and database initialization

- [ ] T015 Create backend/__init__.py
- [ ] T016 Create backend/config/__init__.py
- [ ] T017 Create backend/config/settings.py with pydantic-settings class
- [ ] T018 Create backend/utils/__init__.py
- [ ] T019 Create backend/utils/logging.py with loguru configuration
- [ ] T020 Create backend/database/__init__.py
- [ ] T021 Create backend/database/database.py with async engine and session factory
- [ ] T022 Create backend/database/migrations/__init__.py
- [ ] T023 Create backend/database/migrations/versions/__init__.py

---

## Phase 4: Database Models

**Purpose**: Create all 8 SQLAlchemy models with indexes

- [ ] T024 Create backend/database/models/__init__.py
- [ ] T025 [P] Create Project model in backend/database/models.py
- [ ] T026 [P] Create Chat model in backend/database/models.py
- [ ] T027 [P] Create Message model in backend/database/models.py
- [ ] T028 [P] Create File model in backend/database/models.py
- [ ] T029 [P] Create OCRResult model in backend/database/models.py
- [ ] T030 [P] Create Transcript model in backend/database/models.py
- [ ] T031 [P] Create AppSettings model in backend/database/models.py
- [ ] T032 [P] Create EvaluationResult model in backend/database/models.py
- [ ] T033 Add all 9 Index definitions to backend/database/models.py (from data-model.md Section "Database Indexes")
- [ ] T034 Add foreign key constraints to backend/database/models.py

---

## Phase 5: Backend Skeleton

**Purpose**: Minimal FastAPI app with health endpoint

- [ ] T035 Create backend/main.py with FastAPI app instance
- [ ] T036 Add CORS middleware to backend/main.py for localhost:8501
- [ ] T037 Add GET /health endpoint to backend/main.py
- [ ] T038 Add startup/shutdown events to backend/main.py
- [ ] T039 Add exception handlers to backend/main.py

---

## Phase 6: Frontend Skeleton

**Purpose**: Basic Streamlit layout (sidebar + tabs)

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

---

## Phase 7: Utility Scripts

**Purpose**: Database and Qdrant setup scripts

- [ ] T050 [P] Create scripts/init_db.py that creates SQLite database with all tables
- [ ] T051 [P] Create scripts/setup_qdrant_collection.py that creates industrial_assistant collection
- [ ] T052 [P] Create scripts/generate_secret_key.py that outputs Fernet key
- [ ] T053 [P] Create scripts/verify_environment.py that checks all services

---

## Phase 8: Validation

**Purpose**: Verify everything works

- [ ] T054 Run `python scripts/init_db.py` and verify industrial_ai.db created
- [ ] T055 Run `python scripts/setup_qdrant_collection.py` and verify Qdrant collection created
- [ ] T056 Run `uvicorn backend.main:app --port 8000` in background
- [ ] T057 Run `curl http://localhost:8000/health` and verify returns `{"status":"ok"}`
- [ ] T058 Run `streamlit run frontend/app.py` and verify UI loads with sidebar + tabs
- [ ] T059 Run `python scripts/verify_environment.py` and verify all checks pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Project Structure)**: No dependencies - can start immediately
- **Phase 2 (Config Files)**: No dependencies - can run in parallel with Phase 1
- **Phase 3 (Backend Config)**: Depends on Phase 1 completion
- **Phase 4 (Database Models)**: Depends on Phase 3 completion
- **Phase 5 (Backend Skeleton)**: Depends on Phase 4 completion
- **Phase 6 (Frontend Skeleton)**: No dependencies on backend - can run in parallel with Phases 3-5
- **Phase 7 (Utility Scripts)**: Depends on Phase 4 (models) and backend/main.py
- **Phase 8 (Validation)**: Depends on all previous phases

### Parallel Opportunities

Within each phase, tasks marked [P] can be executed in parallel:

- **Phase 1**: T002-T008 can run in parallel (different directories)
- **Phase 2**: T010-T014 can run in parallel (different config files)
- **Phase 4**: T025-T032 can run in parallel (different models in same file - complete sequentially to avoid conflicts)
- **Phase 6**: T045-T046 can run in parallel (different CSS files)
- **Phase 7**: T050-T053 can run in parallel (different scripts)
- **Phase 8**: All validation tests can run in parallel

### Implementation Strategy

#### MVP (Phase 1 Complete)

1. Complete Phases 1-7 sequentially
2. Run Phase 8 validation
3. Success criteria: All tests pass, health check returns OK, frontend loads

#### For Cheaper LLMs

- Each task has ONE clear action with ONE file path
- No task requires understanding more than 100 lines of context
- Database models (T025-T032) follow exact schema from data-model.md
- Config files follow exact format from plan.md
- CSS tokens follow exact values from plan.md Section 4.1

---

## Notes

- [P] tasks = can run in parallel (different files, no dependencies)
- Models T025-T032 must be in same file but can be written one at a time
- Backend and frontend are independent until Phase 8
- Docker must be running for Qdrant validation (T055)
- Ollama must be running for health check (T057)
- Stop after each phase to validate locally before proceeding