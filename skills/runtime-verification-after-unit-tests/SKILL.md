---
name: runtime-verification-after-unit-tests
description: Unit tests with mocked LLMs pass but miss model-specific behaviors (hedging, language mixing, context overflow). Add a mandatory runtime verification phase against live models before declaring a feature complete.
---

# Runtime Verification After Unit Tests

## When to use this skill

- You have a feature that involves LLM calls (generation, classification, embedding).
- Your unit tests mock the LLM client and test the surrounding logic.
- You are about to declare the feature "complete" based on passing unit tests.
- The feature has mode-specific or language-specific behavior (e.g., Arabic no-match messages, grounded vs. general prompts).

## The pattern

### The gap between unit tests and runtime

| What unit tests verify | What they miss |
|----------------------|----------------|
| State flows correctly through the pipeline | Whether the LLM actually follows the system prompt |
| No-match path returns the correct message | Whether the model invents new hedge phrasings |
| Sources are emitted in the right order | Whether the model hallucinates source citations |
| The classifier receives the right input | Whether the model's YES/NO is accurate for real queries |
| Score thresholds filter correctly | Whether real retrieval scores match expected distributions |

### Runtime verification protocol

For each mode/path in the feature:

```markdown
#### Test [ID] — [Mode] Mode, [Scenario]
- **Query:** "[exact query text]"
- **Expected behavior:** [what should happen]
- **Actual result:** [what actually happened]
- **RAG_TRACE:** [key diagnostic fields from logs]
  - answer_mode=, retrieval_provider=, prompt_mode=
  - qdrant_called=, groundx_called=
  - relevant_chunks=, answer_chars=
- **Pass/Fail:** [result]
- **Fix needed:** [if fail, what to change]
```

### What to test at runtime

1. **Happy path per mode:** Each mode produces the expected type of answer.
2. **Wrong-mode queries:** What happens when a GroundX-mode user asks an audio question? (Should get no-match, not a hallucinated answer.)
3. **Language behavior:** Does the model actually respond in the specified language? Does it mix languages?
4. **Edge scores:** Queries that produce retrieval scores near the threshold — does the system make the right call?
5. **Hedge detection:** Real LLM output that hedges — does the post-LLM safety net catch it?

### Diagnostic logging (RAG_TRACE)

Add structured trace logging that survives into production:

```python
logger.info(
    "RAG_TRACE answer_mode={} retrieval_provider={} prompt_mode={} "
    "qdrant_called={} groundx_called={} relevant_chunks={} answer_chars={}",
    state.get("answer_mode"),
    state.get("retrieval_provider"),
    state.get("prompt_mode"),
    state.get("qdrant_called"),
    state.get("groundx_called"),
    len(state.get("sources", [])),
    len(state.get("answer", "")),
)
```

This trace makes runtime verification fast: instead of reading the full answer, check the trace fields match expectations.

## Anti-patterns (what NOT to do)

- **Declaring "166 tests pass, feature complete."** In this project, 166 backend unit tests passed for the answer_mode feature, covering all 6 phases. But runtime Test D1 revealed that the qwen2.5-egyptian model sometimes ignored the `_STRICT_GROUNDX_SUFFIX` prompt instruction and answered from general knowledge anyway. This led to adding the pre-LLM answerability classifier — a significant architectural change that came AFTER all unit tests passed.
- **Testing only happy paths at runtime.** Runtime Test D1 was a "wrong mode" test (GroundX mode, audio question). Test D2 was another wrong-mode test (audio mode, PDF question). These cross-mode tests caught real bugs that same-mode tests didn't.
- **Skipping runtime verification because "it's the same code as the tests."** The unit tests mock `OllamaClient` and return predetermined strings. The mocks don't test whether: the model follows the system prompt, the model's output matches the expected language, the model's YES/NO classification is accurate for real-world queries, the model's output triggers or doesn't trigger hedge detection.

## Example prompt or code template

```markdown
## Phase 6: Runtime Verification Checklist

### Prerequisites
- [ ] Backend running with real model (not mocked)
- [ ] At least one document indexed per retrieval provider
- [ ] RAG_TRACE logging enabled

### Test Matrix
| Test | Mode | Scenario | Expected | Pass? |
|------|------|----------|----------|-------|
| A | general | General knowledge question | LLM answer, no retrieval | |
| B | groundx | PDF question with indexed docs | Grounded answer with sources | |
| C | audio | Audio question with indexed audio | Grounded answer with audio sources | |
| D1 | groundx | Audio question (wrong mode) | Arabic no-match message, LLM NOT called | |
| D2 | audio | PDF question (wrong mode) | Arabic no-match message or audio-only answer | |
| E | general | Industrial question | General knowledge, no retrieval | |

### For each test, record:
- RAG_TRACE fields (copy from logs)
- Answer text (first 100 chars)
- Sources (if any)
- Whether LLM was called (check trace)
- Pass/Fail + fix description if needed
```

## How we learned this

The answer_mode implementation report (`implementation_report.md`, 2026-06-05) documents Phase 6 in detail. Five manual tests were run against the live qwen2.5-egyptian model:
- Test A (general mode): Passed — Arabic general knowledge answer, no retrieval.
- Test B (audio mode): Passed — grounded answer from audio transcript.
- Test C (GroundX mode): Passed — grounded answer from PDF.
- Test D1 (GroundX mode, audio question): Initially FAILED — model answered from general knowledge despite strict suffix. Fix: added pre-LLM answerability classifier.
- Test D2 (audio mode, PDF question): Passed — audio-only answer returned.

The RAG_TRACE logging pattern (`backend/agent/nodes/answer.py:304-341`) was specifically designed to make runtime verification fast by exposing all decision points in a single structured log line.

## Reusability

Applies to any system where:
- LLM behavior is part of the feature's correctness criteria
- Unit tests mock the LLM and test surrounding logic only
- The system has mode-specific or language-specific behaviors
- Prompt engineering is involved (system prompts, suffix instructions)

Particularly relevant for: RAG applications, chatbot features, AI-assisted workflows, content generation pipelines, any system where "does the model actually do what the prompt says?" is a valid question.
