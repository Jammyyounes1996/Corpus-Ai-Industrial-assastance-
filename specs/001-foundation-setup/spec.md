# Feature Specification: Foundation & Setup

**Feature Branch**: `001-foundation-setup`
**Created**: 2026-05-18
**Status**: Draft
**Input**: Phase 1 requirements from PLAN.md

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Environment Setup (Priority: P1)

Developer can set up a complete development environment from scratch by cloning the repository and following documented installation steps. The environment includes Python dependencies, Docker services, database initialization, and both backend and frontend applications running locally.

**Why this priority**: This is the foundational entry point for all development work. Without a working environment, no other features can be implemented or tested.

**Independent Test**: A new developer can clone the repository, follow the installation instructions, and verify success by running health checks on both backend and frontend services.

**Acceptance Scenarios**:

1. **Given** a fresh system with Python 3.11+ and Docker installed, **When** developer clones repository and follows installation steps, **Then** all dependencies install successfully without errors
2. **Given** a newly created conda environment, **When** developer activates the environment, **Then** all required Python packages are available with correct versions
3. **Given** Docker Desktop is running, **When** developer runs docker-compose up, **Then** Qdrant container starts and is accessible at localhost:6333
4. **Given** the application database has been initialized, **When** developer runs the init_db script, **Then** SQLite database is created with all 8 tables and correct schema
5. **Given** both backend and frontend services are running, **When** developer calls health endpoint, **Then** backend returns status ("ok", "degraded", or "error") with connection status for each service (database, qdrant, ollama)
6. **Given** Streamlit is launched, **When** developer accesses localhost:8501, **Then** UI renders with sidebar and all tab placeholders

---

### User Story 2 - Backend Health Check (Priority: P1)

Developers and monitoring systems can verify that the backend service is operational by calling a health check endpoint. The endpoint reports status of all critical services (database, vector store, and LLM provider).

**Why this priority**: Health checks are essential for monitoring, debugging, and automated deployment verification. They provide immediate feedback on system state.

**Independent Test**: A developer can send a GET request to /health and receive a JSON response indicating the status of all required services.

**Acceptance Scenarios**:

1. **Given** backend service is running, **When** developer sends GET request to /health endpoint, **Then** response includes status "ok" and connection status for database, qdrant, and ollama
2. **Given** database service is available, **When** health check is called, **Then** response shows database status as "connected"
3. **Given** Qdrant service is unavailable, **When** health check is called, **Then** response shows qdrant status as "disconnected"
4. **Given** Ollama service is not running, **When** health check is called, **Then** response shows ollama status as "disconnected"
5. **Given** Ollama service is running but model (gemma4) is not downloaded, **When** health check is called, **Then** response shows ollama status as "model_missing" and overall status as "degraded"

---

### User Story 3 - Database Initialization (Priority: P1)

Developers can initialize the application database with all required tables, indexes, and constraints using a single command. The database is ready for application use immediately after initialization.

**Why this priority**: Database schema is foundational to all data persistence. Without correct initialization, the application cannot store any data.

**Independent Test**: A developer runs the init_db script and can verify the database file exists with all expected tables and proper foreign key relationships.

**Acceptance Scenarios**:

1. **Given** a fresh database state, **When** developer runs init_db script, **Then** SQLite database file is created at the expected path
2. **Given** database initialization completes, **When** developer queries database schema, **Then** all 8 tables exist: Project, Chat, Message, File, OCRResult, Transcript, AppSettings, EvaluationResult
3. **Given** database tables are created, **When** developer checks indexes, **Then** all required indexes are present for query optimization
4. **Given** the AppSettings table exists, **When** developer queries it, **Then** a singleton row exists with id=1 containing default values

---

### User Story 4 - Vector Store Setup (Priority: P1)

Developers can initialize the vector store (Qdrant) with the required collection configuration using a single command. The collection is configured for both dense and sparse vector search.

**Why this priority**: Vector search is core to the RAG functionality. Without the collection properly configured, document retrieval cannot work.

**Independent Test**: A developer runs the setup_qdrant_collection script and can verify the collection exists with correct dimension settings.

**Acceptance Scenarios**:

1. **Given** Qdrant service is running, **When** developer runs setup_qdrant_collection script, **Then** collection named "industrial_assistant" is created
2. **Given** vector collection exists, **When** developer queries collection configuration, **Then** dense vectors are configured for 768 dimensions
3. **Given** vector collection is created, **When** developer checks collection settings, **Then** sparse vector support is enabled for hybrid search

---

### User Story 5 - Configuration Management (Priority: P2)

Developers can configure the application using environment variables with a validated template. The configuration is type-safe and validated at application startup.

**Why this priority**: Centralized configuration management prevents hardcoded values, enables different environments, and provides early validation of configuration errors.

**Independent Test**: A developer can copy .env.example to .env, provide required values, and the application starts without configuration errors.

**Acceptance Scenarios**:

1. **Given** a fresh checkout of the repository, **When** developer copies .env.example to .env, **Then** all required environment variables are documented with default values
2. **Given** .env file is configured, **When** application starts, **Then** configuration is loaded and validated using pydantic-settings
3. **Given** an invalid configuration value is provided, **When** application starts, **Then** startup fails with clear error message indicating which value is invalid
4. **Given** configuration is loaded, **When** application accesses settings, **Then** all values are type-safe and accessible via the settings class

---

### User Story 6 - Frontend Layout Structure (Priority: P2)

Developers have a working Streamlit frontend with the basic page layout (sidebar, tabs, and content areas). The layout is ready for component development in later phases.

**Why this priority**: Having the frontend layout established provides the structure for adding interactive components. It enables parallel development of UI components.

**Independent Test**: A developer runs Streamlit and sees a complete page layout with sidebar on the left and tab content on the right.

**Acceptance Scenarios**:

1. **Given** Streamlit is launched, **When** developer views the application, **Then** sidebar is displayed on the left side of the screen
2. **Given** the application is running, **When** developer navigates between tabs, **Then** each tab displays its placeholder content
3. **Given** custom CSS is loaded, **When** developer views the application, **Then** design tokens (colors, spacing, typography) are applied consistently
4. **Given** the application state is initialized, **When** developer interacts with the UI, **Then** session state variables are properly managed across page interactions

---

## Edge Cases

- What happens when Docker Desktop is not installed or not running? The verify_environment script should detect and warn about missing Docker/containers.
- How does system handle when Qdrant container fails to start? The setup script should provide clear error messages and suggest troubleshooting steps.
- What happens when database file already exists with old schema? The init_db script should either warn before overwriting or use Alembic for migrations.
- What happens when Ollama model is not downloaded? Health check should report "disconnected" but not fail the entire health endpoint.
- What happens when Ollama service is running but required model (gemma4) is not yet downloaded? /health endpoint must return status: "degraded" with ollama field set to "model_missing" - do NOT return 500 error
- What happens when environment variables are missing? Application should fail to start with clear error message indicating which variable is required.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a conda environment definition file (environment.yml) with Python 3.12 and all required dependencies
- **FR-002**: System MUST provide a requirements.txt file with all Python dependencies pinned to exact versions
- **FR-003**: System MUST provide a .env.example template file documenting all required environment variables with descriptions and default values
- **FR-004**: System MUST provide a .gitignore file that excludes environment files, data directories, and Python cache artifacts
- **FR-005**: System MUST provide a docker-compose.yml file defining Qdrant service configuration
- **FR-006**: System MUST provide a settings module using pydantic-settings for type-safe configuration loading
- **FR-007**: System MUST provide a logging module using loguru with structured JSON formatting
- **FR-008**: System MUST provide a database module with SQLAlchemy async engine and session factory
- **FR-009**: System MUST provide database models for 8 entities: Project, Chat, Message, File, OCRResult, Transcript, AppSettings, EvaluationResult
- **FR-010**: System MUST create all required database indexes for query optimization
- **FR-011**: System MUST provide a FastAPI application with CORS middleware enabled for localhost:8501
- **FR-012**: System MUST provide a GET /health endpoint returning connection status of database, Qdrant, and Ollama services
- **FR-013**: System MUST provide startup and shutdown event handlers in FastAPI application
- **FR-014**: System MUST provide a Streamlit application with sidebar and tab navigation
- **FR-015**: System MUST provide CSS styling with design tokens for colors, spacing, and typography
- **FR-016**: System MUST provide an init_db script that creates SQLite database with all tables and default AppSettings row
- **FR-017**: System MUST provide a setup_qdrant_collection script that creates collection with 768-dense vectors and sparse vector support
- **FR-018**: System MUST provide a verify_environment script that checks all prerequisites (Python, Docker, Ollama, database, Qdrant)

### Key Entities

- **Project**: Represents a workspace organizing related chats together with a name and creation timestamp
- **Chat**: Represents a conversation session with title, model configuration, and optional project association
- **Message**: Represents individual messages in a conversation with role, content, thinking steps, and retrieved context
- **File**: Represents uploaded documents (PDF, audio, image) with metadata and indexing status
- **OCRResult**: Represents OCR extraction results from image files
- **Transcript**: Represents transcribed text from audio files with duration and language
- **AppSettings**: Represents singleton application settings including model configuration and theme preferences
- **EvaluationResult**: Represents RAGAS evaluation metrics for chat messages

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developer can complete full environment setup (clone, install, configure) in under 15 minutes
- **SC-002**: Health check endpoint responds in under 100ms
- **SC-003**: Application cold start (both backend and frontend) completes in under 10 seconds
- **SC-004**: Database initialization completes in under 5 seconds
- **SC-005**: Qdrant collection setup completes in under 5 seconds
- **SC-006**: All project structure is created following the planned directory layout
- **SC-007**: Database schema passes all foreign key constraint validations
- **SC-008**: Verify environment script passes all checks (Python version, Docker, Qdrant, database)

## Assumptions

- Developer has Python 3.12+ installed on their system
- Developer has Docker Desktop installed and running for Windows development
- Developer will use Miniconda for Python environment management
- Developer has network access to download Python packages and Docker images
- Ollama service will be installed separately by the developer (not included in this phase)
- Qdrant v1.12.0 is the target version for Docker container
- SQLite will be used as the database (suitable for single-user desktop application)
- Application will run on localhost during development (ports 8000 for backend, 8501 for frontend)
