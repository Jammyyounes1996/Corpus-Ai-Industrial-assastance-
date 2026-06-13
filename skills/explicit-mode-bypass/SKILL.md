---
name: explicit-mode-bypass
description: When users provide an explicit operating mode (e.g., answer_mode=groundx), bypass auto-classification entirely and route deterministically — eliminates classifier errors for known intent.
---

# Explicit Mode Bypass Over Auto-Classification

## When to use this skill

- Your system has an auto-classifier that routes queries to different backends/modes (e.g., "general chat" vs "document QA" vs "audio search").
- The classifier sometimes misroutes queries, especially edge cases (e.g., industrial keywords triggering document retrieval when the user just wants a definition).
- The user or frontend can provide an explicit mode selection (dropdown, parameter, toggle).
- You want deterministic behavior when the user has already decided what they want.

## The pattern

### Architecture: Early return before classifier

```python
async def router_node(state):
    # 1. Reset ALL state (prevent cross-request contamination)
    state["retrieved_context"] = ""
    state["sources"] = []
    state["qdrant_called"] = False
    state["groundx_called"] = False
    
    # 2. Check for explicit mode BEFORE classifier
    answer_mode = state.get("answer_mode")
    if answer_mode is not None:
        if answer_mode == "general":
            state["routes"] = []
            state["mode_decision"] = "general_no_retrieval"
            return state  # early return — no classifier call
        if answer_mode == "groundx":
            state["routes"] = ["groundx"]
            state["groundx_global_search_allowed"] = True
            return state
        if answer_mode == "audio":
            state["routes"] = ["qdrant"]
            state["qdrant_global_audio_search_allowed"] = True
            return state
        # Unrecognized mode → fall through to classifier (safety net)
    
    # 3. Auto-classification only runs when no explicit mode is set
    category = classify_query(state["query"], ...)
    # ... complex classification logic ...
```

### Key principles

1. **Explicit mode is a complete override**, not a hint. When `answer_mode="groundx"`, the classifier does not run at all — no CPU spent, no chance of misrouting.

2. **The default mode must be backward-compatible.** In this project, `answer_mode` defaults to `"general"` via Pydantic schema. Old clients that don't send the field get the default behavior.

3. **Each mode sets its own state deterministically.** The `groundx_global_search_allowed` and `qdrant_global_audio_search_allowed` flags are set explicitly, not derived from classifier output.

4. **Defensive state reset happens BEFORE the mode check.** This prevents context from a previous request leaking into the current one, regardless of which mode is selected.

5. **Unrecognized modes fall through to the classifier** as a safety net, not as an error. This allows adding new modes without breaking old routers.

## Anti-patterns (what NOT to do)

- **Using explicit mode as a classifier input.** Don't feed the mode into the classifier as a feature — this creates a hybrid where the classifier can still override the user's choice. The mode should bypass the classifier entirely.
- **Not resetting state before mode routing.** In this project, the router initially didn't clear `retrieved_context` and `sources` on entry. This caused cross-request contamination where GroundX results from a previous request leaked into a general-mode response. The fix was adding defensive resets at lines 73-78 of `backend/agent/nodes/router.py`.
- **Making the default mode trigger retrieval.** The default `"general"` mode has zero retrieval routes. This means old clients and unrecognized queries fail safe — they get general knowledge instead of potentially irrelevant retrieval results.

## Example prompt or code template

```python
# Schema with explicit mode
class StreamRequest(BaseModel):
    query: str
    answer_mode: Literal["groundx", "audio", "general"] = "general"

# Router with early bypass
async def router_node(state: AgentState) -> AgentState:
    # Defensive reset
    state["retrieved_context"] = ""
    state["sources"] = []
    for flag in RETRIEVAL_FLAGS:
        state[flag] = False
    
    mode = state.get("answer_mode")
    if mode and mode in MODE_CONFIGS:
        config = MODE_CONFIGS[mode]
        state["routes"] = config["routes"]
        state["retrieval_provider"] = config["provider"]
        for k, v in config["flags"].items():
            state[k] = v
        state["mode_decision"] = config["decision"]
        return state  # bypass classifier
    
    # Fallback: auto-classification
    category = classify_query(state["query"], ...)
    ...
```

## How we learned this

The query classifier in `backend/agent/query_classifier.py` uses regex patterns to detect document intent, industrial keywords, greetings, and definition questions. It works well for auto-routing but has inherent limitations with edge cases (e.g., "What is a PLC?" matches both `_INDUSTRIAL_KEYWORDS_EN` and `_DEFINITION_INTENT_EN`). The explicit `answer_mode` field was added to the `StreamRequest` schema in Phase 1 of the answer_mode implementation (`backend/schemas/chat.py`), and the bypass logic was added in Phase 2 (`backend/agent/nodes/router.py:80-103`). Runtime test D1 proved the bypass works: a GroundX-mode query about audio content correctly returned only GroundX results, while the classifier would have routed it to both providers.

## Reusability

Applies to any system with:
- Multi-backend routing (multiple retrieval providers, multiple APIs, multiple model endpoints)
- An auto-classifier that handles the common case but fails on edge cases
- A UI or API that can expose mode selection to the user
- A need for deterministic, testable routing behavior

Particularly relevant for: multi-modal RAG systems, chatbots with tool selection, API gateways with routing logic, agentic systems where the user can specify which tools to use.
