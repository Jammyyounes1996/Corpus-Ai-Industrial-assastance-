# Skills Extracted from Industrial AI Assistant Project

**Extracted:** 2026-06-06
**Sources:** graphify-out/GRAPH_REPORT.md, implementation_report.md, git log (9 commits), AGENTS.md, 8 source files
**Session logs:** OpenCode session logs were not available on disk (no `.opencode/sessions/` directory found).

| Skill | When to use | Origin (commit/session) |
|---|---|---|
| [phased-agent-implementation](phased-agent-implementation/SKILL.md) | Multi-file features spanning schema→routing→logic→frontend→runtime | answer_mode 6-phase rollout, 2026-06-05 |
| [pre-llm-classifier-gate](pre-llm-classifier-gate/SKILL.md) | RAG system where LLM hedges instead of cleanly refusing irrelevant context | answer_mode Phase 4+6, answerability classifier fix |
| [streaming-buffer-before-commit](streaming-buffer-before-commit/SKILL.md) | SSE streaming with post-generation quality gates that might reject the response | answer_mode Phase 4, hedge detection + streaming coupling |
| [explicit-mode-bypass](explicit-mode-bypass/SKILL.md) | Multi-backend routing where user can specify intent, bypassing auto-classifier | answer_mode Phase 2, router.py early return pattern |
| [spec-analyze-before-implement](spec-analyze-before-implement/SKILL.md) | Before implementing from AI-generated specs/plans/tasks | tasks.md required 4 fix commits (3556ec5→5543df1) |
| [token-budget-discipline](token-budget-discipline/SKILL.md) | AI agent sessions on large codebases with context window limits | AGENTS.md creation, commit 5543df1 |
| [runtime-verification-after-unit-tests](runtime-verification-after-unit-tests/SKILL.md) | LLM features where unit tests mock the model and miss model-specific behaviors | answer_mode Phase 6, 166 tests passed but runtime caught prompt-ignoring |
