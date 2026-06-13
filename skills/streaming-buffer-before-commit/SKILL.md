---
name: streaming-buffer-before-commit
description: When SSE-streaming LLM output that might be rejected or replaced post-generation, buffer all tokens before emitting to avoid sending data you cannot retract.
---

# Streaming Buffer-Before-Commit Pattern

## When to use this skill

- You are streaming LLM tokens to the frontend via SSE (Server-Sent Events).
- There is a post-generation check that might reject or replace the entire response (hedge detection, content filter, answerability gate).
- The frontend displays tokens as they arrive and cannot un-display them.
- You need to decide between "stream immediately for fast UX" and "buffer for correctness."

## The pattern

```
                    ┌─ YES ──→ Stream tokens live ──→ Done
                    │
Should we buffer? ──┤
                    │
                    └─ NO (need post-check) ──→ Buffer all tokens
                                                    │
                                            ┌── Check passes ──→ Replay buffered tokens
                                            │
                                            └── Check fails ──→ Emit replacement message
```

### Decision rule

```python
should_buffer = (
    retrieval_provider in ("groundx", "qdrant_audio")
    and prompt_mode == "GROUNDED_RAG"
)
```

Buffer when:
1. The response is grounded in retrieved context (not general knowledge)
2. The retrieval provider has mode-specific no-match behavior
3. There is a post-LLM quality gate (hedge detection, relevance check)

Stream immediately when:
1. General mode — no post-check needed
2. The pre-LLM classifier already approved the context (and score is high enough to skip hedge detection)

### Implementation

```python
async for token in client.generate_stream(...):
    tokens.append(token)
    if not should_buffer:
        await queue.put({"type": "token", "data": emit_token(token)})

# Post-generation check
if should_buffer:
    if hedge_detected(tokens):
        # Replace entire response
        await queue.put({"type": "sources", "data": emit_sources([])})
        await queue.put({"type": "token", "data": emit_token(NO_MATCH_MSG)})
    else:
        # Replay buffered tokens
        for token in tokens:
            await queue.put({"type": "token", "data": emit_token(token)})
        await queue.put({"type": "sources", "data": emit_sources(state["sources"])})
```

### Source event ordering

When buffering, the `sources` SSE event must be emitted at the right time:
- **On rejection:** Emit `sources: []` BEFORE the replacement message
- **On acceptance:** Emit `sources: [...]` AFTER all tokens are replayed
- **On general mode:** Never emit sources at all

## Anti-patterns (what NOT to do)

- **Streaming tokens and then trying to retract them.** SSE is a one-way protocol. Once you emit `data: {"token": "Based on the document..."}`, the frontend has already rendered it. If hedge detection then fires, the user sees the hedged response flash and then get replaced — a broken UX.
- **Always buffering everything.** This kills perceived latency. In this project, general mode and high-confidence grounded mode stream immediately. Only modes with post-generation quality gates buffer. The user sees tokens appear instantly for most queries.
- **Emitting sources before knowing if the answer will be accepted.** If you emit `sources: [{file: "manual.pdf"}]` and then detect a hedge and replace the answer with a no-match message, the frontend shows sources for an answer that says "no information available" — contradictory UX.

## Example prompt or code template

```python
# Template for any streaming node with post-generation quality gate
async def answer_node(state, token_queue):
    should_buffer = needs_post_check(state)
    
    # Optional: run pre-LLM classifier to potentially skip buffering
    if should_buffer:
        is_answerable = await run_answerability_classifier(state)
        if not is_answerable:
            return emit_rejection(state, token_queue)
    
    tokens = []
    async for token in llm.generate_stream(...):
        tokens.append(token)
        if not should_buffer:
            await token_queue.put(make_token_event(token))
    
    full_answer = "".join(tokens)
    
    if should_buffer and is_hedge(full_answer):
        await emit_rejection(state, token_queue)
    elif should_buffer:
        for t in tokens:
            await token_queue.put(make_token_event(t))
        await token_queue.put(make_sources_event(state["sources"]))
    else:
        if state.get("sources") and state["prompt_mode"] == "GROUNDED_RAG":
            await token_queue.put(make_sources_event(state["sources"]))
    
    await token_queue.put(make_done_event())
```

## How we learned this

In the answer_mode implementation (`backend/agent/nodes/answer.py:273-376`), the initial approach streamed tokens immediately for all modes. When post-LLM hedge detection fired for groundx/audio modes, the frontend had already displayed the hedged text. The fix introduced `should_buffer_for_hedge` which gates buffering on the retrieval provider. The test `test_groundx_mode_llm_hedge_response_replaced_with_arabic_message` in `tests/test_answer_mode_phase4.py:321-352` explicitly verifies the SSE event ordering: `["thinking", "sources", "token", "done"]` with empty sources emitted before the replacement message.

## Reusability

Applies to any system that:
- Streams LLM output via SSE, WebSockets, or chunked HTTP
- Has post-generation quality gates (content filters, factuality checks, hedge detection)
- Needs to maintain consistent UX between "accepted" and "rejected" responses
- Has different streaming strategies for different modes/confidence levels

Particularly relevant for: chat applications with RAG, content moderation pipelines, multi-model orchestration where a secondary model validates the primary model's output.
