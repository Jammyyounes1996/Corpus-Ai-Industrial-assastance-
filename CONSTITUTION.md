# Project Constitution

> **Document Type:** Non-negotiable development principles
> **Audience:** Any developer or AI agent (Claude Code) contributing to this project
> **Status:** This document is the ground truth. When in doubt, refer back here.

---

## Preamble

This codebase will be read more than it is written. Every line of code should communicate intent clearly to a human reader. Code should look like it was crafted thoughtfully by an organized engineer — not assembled hastily by a code generator.

These principles are not suggestions. They are constraints. Following them produces software that is maintainable, debuggable, and trustworthy.

---

## Article I — Code Quality

### §1.1 Clean Code Principles

1. **Self-documenting first, comments second.** Names should make comments unnecessary. Add comments only when the *why* cannot be inferred from the *what*.
2. **Functions do one thing.** If a function name needs "and", split it.
3. **Functions stay short.** Target ≤ 30 lines. Hard cap 50 lines. If longer, refactor.
4. **No magic numbers or strings.** Use named constants. Group related constants in module-level `Final` declarations or Enums.
5. **No dead code.** Unused imports, commented-out blocks, and unreachable branches are removed before commit.
6. **No premature abstraction.** Wait for the third occurrence before extracting.

### §1.2 SOLID & DRY

- **Single Responsibility:** Every module, class, and function has one reason to change.
- **Open/Closed:** Extend behavior via composition or strategy, not by editing existing well-tested code.
- **Liskov Substitution:** Subtypes must honor the contract of their base.
- **Interface Segregation:** Prefer many small protocols over one large one.
- **Dependency Inversion:** Depend on abstractions (Protocols, ABCs), not concretions. Inject dependencies; don't construct them inline.
- **DRY:** Repeat knowledge, not characters. Pattern duplication is fine; logic duplication is not.

### §1.3 File Organization

- **One concept per file.** Don't bundle unrelated classes/functions together.
- **File length cap:** 400 lines. Split when exceeded.
- **Import order** (PEP 8):
  1. Standard library
  2. Third-party
  3. Local
  Separated by blank lines. Sorted alphabetically within each group.
- **No wildcard imports** (`from x import *`). Ever.

---

## Article II — Naming Conventions

### §2.1 Python Naming (PEP 8)

| Construct | Convention | Example |
|-----------|-----------|---------|
| Module / file | `lower_snake_case` | `audio_ingestor.py` |
| Package | `lowercase` (short) | `agent`, `retrieval` |
| Class | `PascalCase` | `AgentState`, `QdrantClient` |
| Function / method | `lower_snake_case` | `embed_chunks()`, `run_agent()` |
| Variable | `lower_snake_case` | `chunk_count`, `file_path` |
| Constant | `UPPER_SNAKE_CASE` | `MAX_CHUNK_SIZE`, `DEFAULT_K` |
| Private (module/class) | `_leading_underscore` | `_validate_input()` |
| Type alias | `PascalCase` | `ChunkId = str` |

### §2.2 Naming Rules

1. **Be specific.** `user_query` not `q`. `embedding_dim` not `dim`.
2. **Avoid Hungarian.** No `str_name`, `list_chunks`.
3. **Booleans use predicates.** `is_indexed`, `has_attachments`, `should_retry`.
4. **Functions are verbs.** `parse_pdf()`, not `pdf_parser()`.
5. **Classes are nouns.** `ChunkEmbedder`, not `EmbedChunks`.
6. **No abbreviations** unless industry-standard (e.g., `pdf`, `url`, `http`, `id`).

---

## Article III — Type Safety & Documentation

### §3.1 Type Hints

- **All public functions and methods must have full type annotations** (parameters and return).
- **Use modern syntax** (Python 3.11+):
  - `list[str]` not `List[str]`
  - `dict[str, int]` not `Dict[str, int]`
  - `X | None` not `Optional[X]`
- **Pydantic models** for all I/O at API boundaries.
- **TypedDict** for structured dicts that aren't worth a full class.
- **Protocol** for duck-typed interfaces.

### §3.2 Docstrings

- **Every public module, class, and function has a docstring.**
- **Format:** Google style.
- **Mandatory sections** for non-trivial functions: short summary, `Args`, `Returns`, `Raises` (if applicable).
- **Skip docstrings for trivial accessors** like `__repr__` or one-line wrappers.

Example:
```python
def embed_chunks(chunks: list[str], model: str = "nomic-embed-text") -> list[list[float]]:
    """Generate dense embeddings for a list of text chunks.

    Args:
        chunks: Text strings to embed. Each ≤ 8000 characters.
        model: Ollama embedding model name.

    Returns:
        List of 768-dimensional embedding vectors, one per input chunk.

    Raises:
        OllamaConnectionError: If the Ollama server is unreachable.
        ValueError: If any chunk exceeds 8000 characters.
    """
```

### §3.3 Comments

- **Comment the why, never the what.**
- ✅ `# Use RRF with k=60 — empirically best per Cormack et al. 2009`
- ❌ `# Increment counter by 1`
- **TODO comments** must include an owner and a context: `# TODO(mohamed): switch to async after Phase 6`

---

## Article IV — Error Handling

### §4.1 Exception Strategy

1. **Define custom exception classes** per module domain. Examples:
   - `IngestionError`, `PDFParsingError`, `WhisperTranscriptionError`
   - `RetrievalError`, `QdrantConnectionError`
   - `AgentError`, `NodeExecutionError`
2. **Inherit from a project base:** `class AppError(Exception)`.
3. **Never use bare `except:` or `except Exception:`** unless re-raising after logging.
4. **Fail fast at the boundary.** Validate inputs at API edges with Pydantic. Trust validated data internally.
5. **Errors carry context.** Include relevant IDs, paths, or query info in exception messages.

### §4.2 User-Facing Errors

- API endpoints return structured error responses:
  ```json
  {"error": "PDFParsingError", "message": "GroundX timeout after 60s", "details": {"file_id": "..."}}
  ```
- Frontend translates errors into friendly toast notifications. Never expose stack traces to users.

### §4.3 Retries

- Use `tenacity` for transient failures (network calls).
- Exponential backoff: start 1s, max 30s, 3 attempts.
- Never retry on `4xx` client errors.

---

## Article V — Dependency Management

### §5.1 Library Selection Criteria

A library may be added only if it meets all of:

1. **Active maintenance** — commits within last 6 months.
2. **No license conflict** — MIT, Apache 2.0, or BSD preferred. GPL acceptable only for tools, not libraries.
3. **No transitive conflict** — runs `pip check` clean after install.
4. **Compatible Python version** — supports Python 3.11+.
5. **Documented** — has a real README and API docs.
6. **Necessary** — the standard library or existing dependency can't easily do this.

### §5.2 Version Pinning

- **All dependencies pinned to exact versions** in `requirements.txt`.
- **Pin transitive dependencies too** if they've caused issues (lock with `pip freeze` for known-good combos).
- **Update intentionally**, not opportunistically. Each upgrade is a discrete commit with testing.

### §5.3 Forbidden Patterns

- ❌ Installing packages at runtime (`pip install` in code).
- ❌ Using two libraries that solve the same problem (e.g., both `requests` and `httpx` for HTTP).
- ❌ Adding a library for a single 10-line utility — write it yourself.
- ❌ Heavyweight frameworks for lightweight tasks (no Django for a JSON endpoint).

---

## Article VI — Environment & Configuration

### §6.1 Environment Management

- **Python environment:** Miniconda. Single environment per project.
- **Environment name:** `industrial-ai`.
- **Definition file:** `environment.yml` is canonical; `requirements.txt` mirrors it for pip-only users.
- **Setup command** (documented in README):
  ```bash
  conda env create -f environment.yml
  conda activate industrial-ai
  ```

### §6.2 Configuration

- **All configuration via environment variables.** No hardcoded paths, URLs, or secrets in code.
- **Single source of truth:** `backend/config/settings.py` using `pydantic-settings`.
- **Validation at startup.** App refuses to start with invalid config.
- **`.env.example` is committed.** `.env` is in `.gitignore`.
- **Secrets** (API keys) are loaded into memory only when needed and never logged.

### §6.3 Secrets Handling

- **API keys at rest:** Encrypted with Fernet symmetric encryption in SQLite.
- **Encryption key:** Stored in `SECRET_KEY` env var, generated once and reused.
- **Never log secrets.** Add filters to logging if needed.
- **Never commit secrets.** Pre-commit hook checks for common patterns.

---

## Article VII — Logging

### §7.1 Logging Standards

- **Library:** `loguru` (configured once in `backend/utils/logging.py`).
- **Format:** Structured (JSON in production-like contexts, human-readable in dev).
- **Levels:**
  - `DEBUG` — verbose internals, off by default
  - `INFO` — normal operations (request received, ingestion started)
  - `WARNING` — recoverable issues (retry triggered, fallback used)
  - `ERROR` — operation failed
  - `CRITICAL` — service unhealthy
- **Every log line includes:** timestamp, level, module name, and contextual IDs (chat_id, file_id).

### §7.2 What to Log

- ✅ API requests (method, path, status, duration)
- ✅ External service calls (URL, status, duration)
- ✅ Agent node entry/exit with execution time
- ✅ Errors with full traceback
- ❌ User content (chat messages, file contents) — privacy
- ❌ API keys, tokens, or any secret
- ❌ Personally identifiable information

---

## Article VIII — Asynchronous Code

### §8.1 Async Discipline

- **FastAPI handlers:** `async def` for I/O-bound operations.
- **Don't mix sync and async carelessly.** Use `asyncio.to_thread()` for blocking calls inside async functions.
- **No `time.sleep()` in async code.** Use `await asyncio.sleep()`.
- **HTTP client:** `httpx.AsyncClient`, never `requests` inside async paths.
- **Database:** `aiosqlite` via SQLAlchemy 2.0 async API.

### §8.2 Streaming

- **SSE streams** use `sse-starlette` and `EventSourceResponse`.
- **Backpressure:** Don't buffer entire responses; yield as available.
- **Always send a final `done` event** so clients know to close.

---

## Article IX — Testing

### §9.1 Test Coverage

- **Minimum coverage:** 70% for `backend/core/` modules.
- **Critical paths:** 90%+ coverage (agent graph, retrieval, ingestion).
- **Test pyramid:** Many unit tests, fewer integration tests, minimal end-to-end.

### §9.2 Test Structure

- Mirror source tree: `tests/backend/core/test_<module>.py`.
- **Naming:** `test_<function>_<scenario>_<expected>()`.
  - Example: `test_embed_chunks_empty_list_returns_empty()`.
- **One assertion per test** when possible.
- **Use fixtures** in `conftest.py` for shared setup.

### §9.3 Test Hygiene

- **Tests are isolated.** No test depends on another's state.
- **No network calls** in unit tests. Mock external services.
- **Test data** lives in `tests/fixtures/`. Never in test files.

---

## Article X — Frontend Standards (Streamlit)

### §10.1 Component Discipline

- **Each component in its own file** under `frontend/components/`.
- **Components are functions**, not classes. Streamlit is functional.
- **State management:** Use `st.session_state` deliberately. Initialize keys explicitly at app start.
- **No business logic in components.** Components render; logic lives in `frontend/utils/`.

### §10.2 CSS Discipline

- **All custom CSS in `frontend/styles/main.css`.** No inline `style=` attributes.
- **Use CSS custom properties** (variables) for theming.
- **BEM-ish naming** for custom classes: `.thinking-card__header`, `.message-card--ai`.
- **No `!important`** unless overriding Streamlit defaults that can't be avoided.

### §10.3 API Calls

- **All HTTP/SSE calls** go through `frontend/utils/api_client.py`.
- **No `requests.get()` scattered in components.**
- **Handle errors at the API client layer.** Components receive either data or a user-friendly error message.

---

## Article XI — Git & Version Control

### §11.1 Commits

- **Conventional Commits** format:
  ```
  feat(agent): add OCR node to graph
  fix(ingest): handle empty PDFs gracefully
  refactor(retrieval): extract RRF into separate function
  docs(readme): add troubleshooting section
  test(agent): cover router node edge cases
  ```
- **One logical change per commit.** Don't combine refactoring + feature.
- **Commit message body** explains *why* when not obvious from the subject.

### §11.2 Branching

- **`main`** — always working. Demo-able at all times.
- **Feature branches:** `feat/<short-name>`, e.g., `feat/ragas-evaluator`.
- **Squash merge** to main with a clean Conventional Commits message.

### §11.3 .gitignore

Must include:
```
# Python
__pycache__/
*.pyc
.pytest_cache/
.coverage
htmlcov/

# Environments
.venv/
venv/
.env

# Data
data/uploads/
data/audio/
data/images/
qdrant_storage/
*.db

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
```

---

## Article XII — README Standards

The `README.md` is the front door. It must contain, in order:

1. **Project title + one-line description**
2. **Hero screenshot or GIF** of the working app
3. **Table of contents**
4. **Features** — bulleted list
5. **Tech stack** — table with logos/links
6. **Prerequisites** — Python version, Docker, Ollama, etc.
7. **Installation** — step-by-step, copy-pasteable commands
   - Clone repo
   - Create conda environment
   - Pull Ollama models
   - Start Qdrant via docker-compose
   - Initialize database
   - Configure `.env`
8. **Usage** — how to launch backend, frontend, and use each tab
9. **Architecture** — link to `docs/architecture.md`, brief diagram
10. **API Reference** — link to `docs/api.md`
11. **Configuration** — env vars table with descriptions and defaults
12. **Troubleshooting** — common errors and fixes
13. **Project Structure** — tree of folders with descriptions
14. **Contributing** — link to CONSTITUTION.md
15. **License** — MIT
16. **Acknowledgements** — credits for major libraries

**Quality bar:** A new developer should be able to clone the repo and have it running locally in under 15 minutes following only the README.

---

## Article XIII — Performance

### §13.1 General Principles

- **Measure before optimizing.** Use timing logs, not guesses.
- **Cache expensive computations.** Embeddings for unchanged text, model loading.
- **Stream large responses.** Don't accumulate then return.
- **Lazy load.** Don't pull a model into memory until first request needs it.

### §13.2 Targets

- **First token latency** (chat): < 3 seconds on RTX 3060
- **PDF ingestion** (10 pages): < 30 seconds
- **Audio transcription** (5 min audio): < 90 seconds with `base` model
- **OCR on single image:** < 10 seconds
- **App cold start:** < 10 seconds for both frontend and backend

---

## Article XIV — Security

### §14.1 Input Validation

- **Validate everything at the API boundary** with Pydantic.
- **File upload limits** (enforced at FastAPI boundary, HTTP 413 on violation):
  - PDF: max 100 MB, MIME type `application/pdf` only
  - Audio: max 100 MB, MIME types: `audio/mpeg`, `audio/wav`, `audio/m4a`, `audio/ogg`, `audio/mp4`
  - Image: max 25 MB, MIME types: `image/jpeg`, `image/png`, `image/webp`
- **Sanitize filenames** before saving (no path traversal, max 255 characters).

### §14.2 SQL Safety

- **Always use SQLAlchemy ORM or parameterized queries.** Never string concatenation.

### §14.3 CORS

- **Whitelist only known origins.** For local dev: `http://localhost:8501`.

---

## Article XV — Definition of Done

A task is **done** only when:

- [ ] Code follows all articles of this constitution.
- [ ] Type hints present on all new functions.
- [ ] Docstrings on all public APIs.
- [ ] Tests written and passing.
- [ ] `pip check` reports no conflicts.
- [ ] `ruff check` reports no errors.
- [ ] `mypy` reports no errors on new code.
- [ ] Manually tested in the running app.
- [ ] No new TODOs without an owner.
- [ ] README updated if user-facing change.
- [ ] Commit message follows Conventional Commits.

---

## Article XVI — Amendments

This constitution may be amended only by explicit user request, with the change discussed and the document updated in a dedicated commit (`docs(constitution): ...`).

When in doubt, choose the option that produces clearer code over the option that produces less code.

---

**End of Constitution**

> *"Code is read far more often than it is written. Optimize for the reader."*