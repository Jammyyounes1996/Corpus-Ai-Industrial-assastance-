---
name: phased-agent-implementation
description: Split multi-file features into sequential phases with per-phase test files and cumulative test counts, verified by runtime testing as the final phase.
---

# Phased Agent Implementation

## When to use this skill

- A feature touches more than 3 source files across multiple layers (schema, routing, logic, frontend).
- The feature involves LLM behavior that cannot be fully validated by unit tests alone.
- You are building a pipeline where each stage depends on the output of the previous stage (e.g., request → state → router → retrieval → context → answer).
- The user asks to "implement feature X" and X has both backend and frontend components.

## The pattern

1. **Decompose by data flow, not by file.** Each phase should represent a coherent slice of the data flow that can be tested independently.

2. **Phase structure:**
   - Phase 1: Schema + State — Define the new fields, types, and validation. Test: schema accepts/rejects correctly.
   - Phase 2: Routing/Decision — Wire the new fields into routing logic. Test: routing produces correct outputs for each mode.
   - Phase 3: Processing guards — Each processing node respects the new fields. Test: nodes skip/execute based on state.
   - Phase 4: Core logic — The main business logic (context synthesis, answer generation). Test: full node behavior.
   - Phase 5: Frontend integration — UI components, API calls. Test: component renders, sends correct payloads.
   - Phase 6: Runtime verification — Manual tests against a live backend with real models.

3. **Per-phase test files:** Create `tests/test_<feature>_phase<N>.py` for each phase. Track cumulative test counts (e.g., "132 baseline + 7 new = 139 total").

4. **No phase proceeds until the previous phase's tests pass.** This catches integration issues at each boundary instead of at the end.

5. **Phase 6 is mandatory for LLM features.** Unit tests mock the LLM and cannot catch model-specific behaviors like hedging, language mixing, or context window overflow.

## Anti-patterns (what NOT to do)

- **Implementing all phases in one session.** In this project, the answer_mode feature was implemented across 6 phases with tests at each boundary. Attempting all at once would have missed the streaming-decision coupling bug (Phase 4) that only appeared when answer buffering interacted with hedge detection.
- **Skipping Phase 6 because "all tests pass."** 166 backend tests passed, but runtime Test D1 revealed that the LLM would sometimes ignore the strict suffix and answer from general knowledge. The pre-LLM classifier was added as a fix discovered during Phase 6.
- **Organizing phases by file instead of by data flow.** "Phase 1: edit answer.py, Phase 2: edit context.py" creates phases where each phase is untestable in isolation. Data flow slicing (schema → routing → processing → logic → UI → runtime) ensures each phase has a clear contract.

## Example prompt or code template

```
Implement [FEATURE] using a phased approach.

Phase 1: Schema + State
- Add [field] to [SchemaClass] with type [Literal/enum/str] and default [value]
- Add [N] new fields to [StateClass]: [field1], [field2], ...
- Create tests/test_[feature]_phase1.py with [N] test cases
- Run tests, report count: [baseline] + [new] = [total]

Phase 2: Router/Decision Logic
- In [router_file], add branching for [field] before existing classifier logic
- For each [mode]: set routes, provider, and decision fields
- Create tests/test_[feature]_phase2.py
- Run tests, report cumulative count

Phase 3-4: [Processing + Core Logic — same pattern]

Phase 5: Frontend Integration
- Add type definitions, wire into API call, add UI component
- Create component test file

Phase 6: Runtime Verification
- Start backend with real model
- Test each mode against live endpoints
- Document: query, result, RAG_TRACE fields, pass/fail
```

## How we learned this

The answer_mode feature (2026-06-05, documented in `implementation_report.md`) was implemented across 6 phases. Phase 4 tests (16 tests in `tests/test_answer_mode_phase4.py`) caught the hedge detection / streaming coupling issue before it reached the frontend. Phase 6 runtime tests against the qwen2.5-egyptian model caught cases where the LLM ignored prompt suffixes, leading to the pre-LLM answerability classifier. The per-phase test files (`test_answer_mode_phase1.py` through `phase4.py`) allowed precise regression tracking: 126 → 132 → 139 → 150 → 166 backend tests.

## Reusability

Applies to any multi-layer feature in a RAG/agent system, data pipeline, or full-stack application where:
- Multiple backend nodes/services must coordinate
- LLM behavior is involved and cannot be fully unit-tested
- Frontend and backend must agree on a contract
- The feature has distinct modes or configurations that affect the entire pipeline
