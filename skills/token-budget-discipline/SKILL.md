---
name: token-budget-discipline
description: Enforce hard limits on file reads (10), retries (2), and tasks per session (2) when working with AI coding agents to prevent token explosion from unbounded exploration and retry loops.
---

# Token Budget Discipline for AI Agent Sessions

## When to use this skill

- You are working with an AI coding agent (Claude Code, OpenCode, Cursor, etc.) on a large codebase.
- The agent has a tendency to read too many files, retry failing operations in loops, or attempt too many tasks in one session.
- Previous sessions burned through context windows or hit token limits before completing the task.
- The codebase has large generated files, lock files, or binary files that waste tokens if read.

## The pattern

### Hard limits (non-negotiable)

| Resource | Limit | What happens at limit |
|----------|-------|----------------------|
| Files read per task | 10 | STOP and ask user which files are actually needed |
| Retry attempts per operation | 2 | STOP and report the error to user |
| Tasks per session | 2 | STOP and wait for user confirmation |
| Same command repeated | 2 | STOP — something is wrong with the approach |
| Files modified at once | 5 | STOP — task is too large, needs splitting |

### Never-read list

```
node_modules/     qdrant_storage/     logs/        dist/      build/
*.db              *.sqlite            *.pdf        *.png      *.jpg
package-lock.json yarn.lock           uv.lock      *.pyc
```

### Graphify-first protocol

Before opening any source file:
1. Check if `graphify-out/GRAPH_REPORT.md` exists
2. Use `graphify query "<question>"` for targeted questions
3. Use `graphify path "<A>" "<B>"` for relationship questions
4. Only open source files when the graph points you to specific files

This typically reduces file reads from 15-20 down to 3-5 per task.

### Error handling protocol

```
error → fix attempt 1 → error → fix attempt 2 → error → STOP & REPORT

STOPPED: [reason]
Last action: [what was done]
Error: [exact error message]
Next step needed: [what the user should decide]
```

### Session structure

```
1. Read task requirements (from tasks.md or user message)
2. Identify minimum files needed (max 10)
3. Read only those files
4. Implement the task
5. Run verification (max 1 attempt)
6. If verification fails → try once more → if still fails → STOP & REPORT
7. Mark task complete and WAIT for user
```

## Anti-patterns (what NOT to do)

- **Reading files "just in case."** In this project, the agent would sometimes read 20+ files before starting a 3-file task. The graphify-first protocol was added to `AGENTS.md` specifically to prevent this — the knowledge graph can answer "which files are related to X?" without reading them.
- **Retry loops on build/test failures.** The `AGENTS.md` file (lines 50-68) explicitly forbids auto-fix loops: `error → fix → error → fix → error → fix → ...`. This pattern burns through the entire context window and usually doesn't converge. The correct behavior is to stop after 2 attempts and let the user diagnose.
- **Implementing an entire phase in one session.** The agent execution limits in `AGENTS.md` cap at 2 tasks per session. A full phase might have 10-15 tasks — attempting all in one session leads to context overflow and increasingly degraded output quality as the window fills up.
- **Reading lock files or generated files.** `package-lock.json` alone can be 10,000+ lines. Reading it provides no useful information for implementation tasks and wastes a significant portion of the context window.

## Example prompt or code template

```markdown
# AGENTS.md template section for token budget

## Token Budget Rules — CRITICAL

### File Reading Limits
- Read a maximum of [10] files per task
- NEVER read: [never-read list]
- If a task requires more than [10] files → STOP and ask the user

### Execution Limits
- Implement a maximum of [2] tasks per session
- After each task → STOP and wait for user confirmation
- Do NOT proceed to next task automatically

### Retry & Error Rules
- Maximum retry attempts: [2] for any failing operation
- If the same error appears twice → STOP, report to user, wait
- Do NOT attempt auto-fix loops on build/test failures

### Graphify-First (if available)
- Before reading source files, check graphify-out/GRAPH_REPORT.md
- Use graphify query/path/explain for targeted questions
- Only open source files the graph points you to
```

## How we learned this

The `AGENTS.md` file in this project (committed in 5543df1) was created after multiple sessions where the agent burned through context windows. The specific rules — 10 file limit, 2 retry limit, 2 task limit, never-read list — were calibrated based on actual session failures. The graphify integration was added later (visible in `AGENTS.md:157-168`) as an additional token-saving measure. The project's knowledge graph (3052 nodes, 4056 edges per `graphify-out/GRAPH_REPORT.md`) allows answering most architectural questions without reading source files.

## Reusability

Applies to any project where:
- AI coding agents are used for implementation
- The codebase is large enough that unbounded exploration wastes tokens
- Sessions have context window limits (all current LLM-based agents)
- The team has experienced token explosion from retry loops or file over-reading

Particularly relevant for: enterprise codebases, monorepos, projects with generated code, any codebase > 50 files where targeted reading is more efficient than full exploration.
