# AGENTS.md — Industrial AI Assistant

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read `specs/006-known-limitations-fix/plan.md`.
<!-- SPECKIT END -->

---

## 🧠 Project Identity

You are an AI coding agent working on the **Industrial AI Assistant** —
a production-grade RAG system for Egyptian petrochemical plants.

**Tech Stack:**
- Backend: FastAPI + Python
- Vector DB: Qdrant (hybrid search: dense + sparse BM25)
- Graph DB: Neo4j
- LLM: Ollama (local models)
- Embedding: nomic-embed-text (768 dimensions)
- Frontend: React
- Database: SQLite / PostgreSQL

---

## ⛔ Token Budget Rules — CRITICAL

These rules exist to prevent token waste. Follow them strictly.

### File Reading Limits
- Read a **maximum of 10 files** per task
- NEVER read `node_modules/`, `qdrant_storage/`, `logs/`, `dist/`, `build/`
- NEVER read binary files: `*.db`, `*.sqlite`, `*.pdf`, `*.png`, `*.jpg`
- NEVER read lock files: `package-lock.json`, `yarn.lock`, `uv.lock`
- If a task requires more than 10 files → **STOP and ask the user**

### Execution Limits
- Implement a **maximum of 2 tasks** per session
- After each task → **STOP and wait for user confirmation**
- Do NOT proceed to next task automatically
- Do NOT implement an entire phase in one session

### Context Management
- Do NOT load the entire project structure at session start
- Only read files **directly needed** for the current task
- If you already read a file this session → do NOT read it again

---

## 🔁 Retry & Error Rules — NO LOOPS

Retry loops are the #1 cause of token explosion. Follow strictly.

- **Maximum retry attempts: 2** for any failing operation
- If the same error appears twice → **STOP, report to user, wait**
- Do NOT attempt auto-fix loops on build/test failures
- Do NOT run the same command more than 2 times
- On dependency conflicts → report, do NOT auto-resolve
- On import errors → report the exact error, do NOT loop

**Wrong behavior:**
```
error → fix → error → fix → error → fix → ... (infinite loop)
```

**Correct behavior:**
```
error → fix attempt 1 → error → fix attempt 2 → error → STOP & REPORT
```

---

## ✅ Task Execution Protocol

Follow this exact sequence for every task:

```
1. Read the task requirements (from tasks.md or user message)
2. Identify the minimum files needed (max 10)
3. Read only those files
4. Implement the task
5. Run verification (max 1 attempt)
6. If verification fails → try once more → if still fails → STOP & REPORT
7. Mark task complete and WAIT for user
```

---

## 📋 Task Size Rules

| Task Type | Max Files to Read | Max Retries |
|-----------|-------------------|-------------|
| Create new file | 3 files | 2 |
| Edit existing file | 5 files | 2 |
| Add API endpoint | 5 files | 2 |
| Database migration | 4 files | 2 |
| Full feature | Split into smaller tasks | — |

---

## 🛑 Hard Stop Conditions

Stop immediately and report to user when:

- Same error appears more than 2 times
- Task requires reading more than 10 files
- A command runs for more than 60 seconds
- You are about to modify more than 5 files at once
- You are unsure which approach to take

**When stopping, always report:**
```
STOPPED: [reason]
Last action: [what was done]
Error: [exact error message]
Next step needed: [what the user should decide]
```

---

## 🏗️ Project Structure Reference

Only read files inside these directories when relevant to the task:

```
backend/
  app/
    api/          ← API endpoints
    core/         ← config, database, utils
    models/       ← SQLAlchemy models
    services/     ← business logic
  main.py

frontend/
  src/
    components/
    pages/
    services/

specs/
  001-foundation-setup/
  002-ingestion-pipeline/

PLAN.md           ← read this for architecture decisions
CONSTITUTION.md   ← read this for coding standards
```

---

## 💬 Communication Style

- Always respond in **English**
- Before starting any task → state: what files you will read and why
- After completing a task → state: what was done, what was changed
- When stopping → state: exact reason and what the user needs to decide

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
