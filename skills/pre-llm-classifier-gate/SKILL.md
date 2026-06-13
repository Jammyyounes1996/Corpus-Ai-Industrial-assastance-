---
name: pre-llm-classifier-gate
description: Use a cheap binary LLM classifier call BEFORE the main answer generation to decide if retrieved context is answerable, preventing hallucinated or hedged responses.
---

# Pre-LLM Classifier Gate for RAG No-Match Detection

## When to use this skill

- You have a RAG system that retrieves chunks and feeds them to an LLM for answer generation.
- The LLM sometimes generates hedging responses like "the context does not contain..." instead of cleanly refusing.
- You need deterministic no-match behavior (e.g., a fixed Arabic/English message) that the LLM cannot override.
- Post-LLM string detection is failing because the LLM keeps inventing new hedge phrasings.

## The pattern

### Three-layer defense (ordered by reliability)

**Layer 1: Pre-LLM answerability classifier (most reliable)**
```python
# Cheap LLM call: "Can this context answer this question? YES or NO"
classifier_tokens = await client.generate_stream(
    prompt=build_answerability_prompt(query, retrieved_context),
    system=ANSWERABILITY_SYSTEM_PROMPT,
    temperature=0.0,  # deterministic
    max_tokens=8,      # only need YES/NO
)
decision = "".join(classifier_tokens)
if not decision.strip().upper().startswith("YES"):
    # Check Layer 1b: score override
    if max_retrieval_score >= 0.65:
        pass  # high-confidence retrieval overrides classifier
    else:
        return NO_MATCH_MESSAGE  # skip main LLM entirely
```

**Layer 2: Relevance score threshold (in context synthesis)**
```python
# Before even reaching the answer node, filter low-score chunks
GROUNDX_THRESHOLD = 0.55
AUDIO_THRESHOLD = 0.48
if max_chunk_score < threshold:
    state["prompt_mode"] = "CONSERVATIVE_NO_SOURCE"
    state["no_match_message_type"] = f"{provider}_no_match"
```

**Layer 3: Post-LLM hedge detection (safety net)**
```python
HEDGE_SIGNALS = (
    "no specific mention", "not mentioned", "does not contain",
    "no information", "cannot answer", ...
)
if any(signal in answer.lower() for signal in HEDGE_SIGNALS):
    return NO_MATCH_MESSAGE  # override the hedged answer
```

### Key design decisions

1. The classifier system prompt must explicitly say "Do NOT require exact keyword matches" — otherwise it rejects semantic matches (e.g., "American protection" vs "US military bases").
2. Score override (Layer 1b) prevents the classifier from rejecting high-confidence retrievals where the LLM phrased its NO incorrectly.
3. Layer 3 is the least reliable but catches cases where Layers 1-2 both miss.

## Anti-patterns (what NOT to do)

- **Relying solely on post-LLM string matching.** In this project, the `_HEDGE_SIGNALS` tuple grew to 18+ entries and still missed new hedge phrasings the LLM invented. The LLM is creative — it will always find new ways to say "I don't know." The pre-LLM classifier reduces the problem to a binary YES/NO decision.
- **Adding strict prompt suffixes and hoping the LLM obeys.** The `_STRICT_GROUNDX_SUFFIX` and `_STRICT_AUDIO_SUFFIX` in `backend/agent/nodes/answer.py` tell the LLM to respond with an exact Arabic message when it can't answer. Runtime testing showed the qwen2.5 model sometimes ignored this and answered from general knowledge anyway. Prompt instructions are suggestions to the LLM, not guarantees.
- **Using the same relevance threshold for all retrieval providers.** GroundX scores and Qdrant scores have different distributions. This project uses 0.55 for GroundX and 0.48 for audio — calibrated by observing actual score distributions during runtime testing.

## Example prompt or code template

```python
# Answerability classifier system prompt template
ANSWERABILITY_SYSTEM_PROMPT = """You are a binary relevance classifier.
Decide whether the CONTEXT can help answer the QUESTION.

Reply YES if:
- Context discusses the same topic, entities, or concepts
- Context provides related background information
- Context contains facts related to the question's subject

Reply NO only if the context is on a completely unrelated topic.

Do NOT require exact keyword matches.
Respond with exactly one word: YES or NO."""

# Usage in answer node
async def answer_node(state):
    if should_check_answerability(state):
        is_answerable = await run_classifier(state["query"], state["retrieved_context"])
        if not is_answerable and max_score < SCORE_OVERRIDE_THRESHOLD:
            return emit_no_match_message(state["retrieval_provider"])
    # ... proceed with main LLM call
```

## How we learned this

During Phase 6 runtime verification of the answer_mode feature (2026-06-05), Test D1 (GroundX mode with an audio question) revealed that the LLM would sometimes answer from general knowledge despite the strict suffix instruction. The fix evolved through three iterations: first adding more hedge strings to `_HEDGE_SIGNALS` (failed — LLM kept inventing new phrasings), then adding the pre-LLM answerability classifier (worked but was too aggressive), then adding the score override at 0.65 (balanced). See `backend/agent/nodes/answer.py:141-176` for the classifier implementation and `tests/test_answer_mode_phase4.py:317-680` for the 16+ tests covering all three layers.

## Reusability

Applies to any RAG system where:
- Retrieved chunks may be irrelevant to the user's question
- The LLM must not hallucinate answers from irrelevant context
- Deterministic no-match behavior is required (fixed messages, specific languages)
- The system has multiple retrieval providers with different score distributions

Particularly relevant for: industrial AI assistants, medical RAG, legal document QA, multilingual RAG systems.
