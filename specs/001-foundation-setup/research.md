# Research: Foundation & Setup

**Feature**: 001-foundation-setup
**Date**: 2026-05-18
**Status**: Complete

---

## Summary

This document consolidates research findings for unknowns identified during planning. All critical technical decisions have been validated with concrete evidence and citations.

---

## R1: Ollama Model Compatibility

### Question
Verify Gemma4 works with langchain-ollama 0.2.0 on Windows.

### Research
- Ollama supports Gemma 4 (latest Google model) via `ollama pull gemma4`
- langchain-ollama 0.2.0 supports all Ollama models through the standard chat/embedding interfaces
- Windows support is native; Ollama runs as a service
- Gemma4-9b-instruct is available locally (confirmed via `ollama list`)
- Vision capabilities available via `gemma4` for OCR

### Decision
**Use `gemma4:latest` (Gemma 4 4B Instruct).**
- Gemma 4 is the user's installed model (9.6 GB, 3 weeks ago)
- Local installation confirmed via `ollama list`
- Compatible with langchain-ollama 0.2.0
- Vision capabilities available via `gemma4` for OCR

### Sources
- [Ollama Model Library - Gemma4](https://ollama.com/library/gemma4)
- [LangChain Ollama Documentation](https://python.langchain.com/docs/integrations/platforms/ollama/)

---

## R2: Qdrant Docker on Windows

### Question
Confirm Qdrant runs correctly via Docker Desktop on Windows.

### Research
- Qdrant 1.12+ provides official Docker images for Windows/amd64
- Docker Desktop (Windows 10/11) supports Linux containers
- Port 6333 (HTTP) and 6334 (gRPC) are the standard ports
- Volume persistence works via Windows bind mounts
- Hybrid search (dense + sparse) is fully supported

### Decision
**Use Qdrant 1.12.0 via docker-compose.yml.**
- Proven stability for vector search
- Hybrid search capability required for RRF fusion
- Single container deployment is sufficient for local use

### Sources
- [Qdrant Docker Documentation](https://qdrant.tech/documentation/guides/docker/)
- [Qdrant Hybrid Search](https://qdrant.tech/documentation/concepts/hybrid_search/)
- [Docker Desktop Windows Requirements](https://docs.docker.com/desktop/install/windows-install/)

---

## R3: Miniconda + PowerShell Workflow

### Question
Validate environment creation workflow on Windows with PowerShell.

### Research
- Miniconda for Windows installer includes PowerShell integration
- `conda env create -f environment.yml` works in PowerShell 5.1+
- `conda activate industrial-ai` activates the environment
- Virtual environment isolation works correctly
- pip requirements are installed within the conda env

### Decision
**Standard Miniconda workflow documented in README.**
- Windows users run Miniconda installer
- Environment creation: `conda env create -f environment.yml`
- Activation: `conda activate industrial-ai`
- All commands work in both PowerShell and Windows Terminal

### Sources
- [Conda Managing Environments](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html)
- [Conda on Windows](https://docs.conda.io/projects/conda/en/latest/user-guide/install/windows.html)

---

## R4: FastAPI CORS Configuration with Streamlit

### Question
Specific configuration needed for FastAPI CORS with Streamlit on localhost:8501.

### Research
- FastAPI requires `CORSMiddleware` to allow cross-origin requests
- Streamlit runs on `http://localhost:8501` by default
- FastAPI backend runs on `http://localhost:8000` by default
- Allow origins: `["http://localhost:8501"]` for local development
- Allow credentials: `True` (for future cookie/session support)
- Allow methods: `["*"]` (GET, POST, PUT, DELETE)
- Allow headers: `["*"]`

### Decision
**Configure FastAPI with CORSMiddleware in main.py:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Sources
- [FastAPI CORS Documentation](https://fastapi.tiangolo.com/tutorial/cors/)
- [Streamlit Deployment Options](https://docs.streamlit.io/deploy)

---

## R5: LangGraph SSE Streaming

### Question
Confirm LangGraph astream_events works reliably with sse-starlette.

### Research
- LangGraph 0.2+ supports `astream_events()` for real-time node execution events
- sse-starlette 2.1+ provides `EventSourceResponse` for FastAPI SSE
- Event types: `on_chain_start`, `on_chain_end`, `on_chat_model_stream`
- Each event can be mapped to a thinking step in the UI
- Streaming approach yields each token as it's generated

### Decision
**Use LangGraph's `astream_events()` + sse-starlette's `EventSourceResponse`.**
- Mapping: `on_chain_start` → "⟳ Step in progress"
- Mapping: `on_chain_end` → "✓ Step completed"
- Mapping: `on_chat_model_stream` → token stream
- Final event: `done` to close SSE connection

### Sources
- [LangGraph Streaming Documentation](https://langchain-ai.github.io/langgraph/how-tos/streaming/)
- [SSE Starlette Documentation](https://github.com/sysid/sse-starlette)

---

## R6: SQLAlchemy 2.0 Async Patterns

### Question
Best practices for SQLAlchemy 2.0 async with aiosqlite.

### Research
- SQLAlchemy 2.0 introduces 2.0-style async querying
- `create_async_engine()` with `sqlite+aiosqlite://` connection string
- `AsyncSession` from `sqlalchemy.ext.asyncio`
- Async context manager for session lifecycle
- `select()` construct with `await session.execute()`
- Alembic supports async migrations with `run_migrations_online()`

### Decision
**Use SQLAlchemy 2.0 async patterns throughout.**
- Engine: `create_async_engine(DATABASE_URL)`
- Session factory: `async_sessionmaker(engine, expire_on_commit=False)`
- Query pattern:
  ```python
  async with async_session_maker() as session:
      result = await session.execute(select(Chat).where(Chat.id == chat_id))
      return result.scalar_one_or_none()
  ```
- Migrations: Use Alembic with async engine

### Sources
- [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [AsyncioSQLite Documentation](https://aiosqlite.omnilib.dev/)
- [Alembic Async Migrations](https://alembic.sqlalchemy.org/en/latest/api/connections.html#sqlalchemy.ext.asyncio.AsyncConnection)

---

## Summary of Findings

| Research Item | Decision | Impact |
|---------------|----------|--------|
| Ollama Model | Use `gemma4:latest` (user's installed model) | Update PLAN.md references |
| Qdrant Docker | Use v1.12.0 via docker-compose.yml | Standard deployment |
| Miniconda | Standard conda workflow | README documentation |
| FastAPI CORS | Configure CORSMiddleware for localhost:8501 | Enable frontend-backend comms |
| LangGraph SSE | astream_events + EventSourceResponse | Real-time thinking steps |
| SQLAlchemy 2.0 | Full async patterns with aiosqlite | All database operations async |

**All unknowns resolved. Proceed to Phase 1.**