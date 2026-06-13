---
name: spec-analyze-before-implement
description: Run a structured analysis pass on spec/plan/tasks artifacts BEFORE implementation begins — catches contract mismatches, missing edge cases, and dependency errors that would become bugs.
---

# Spec-Analyze-Before-Implement

## When to use this skill

- You have generated a spec, plan, or tasks file using an AI agent or template system.
- You are about to begin implementation based on these artifacts.
- The feature involves multiple interacting components (backend + frontend, multiple API endpoints, database changes + business logic).
- Previous implementations from similar artifacts had bugs that could have been caught by reading the spec more carefully.

## The pattern

### The SDD (Spec-Driven Development) workflow

```
specify → clarify → plan → tasks → ANALYZE → implement
                                      ↑
                              This step catches bugs
                              before code is written
```

### What the analysis step checks

1. **Cross-artifact consistency:** Do the field names in `spec.md` match the field names in `contracts/api.md`? Does `plan.md` reference all entities from `data-model.md`?

2. **Missing edge cases:** Does the spec define behavior for empty inputs, null fields, error states, and backward compatibility?

3. **Dependency ordering in tasks:** Can Task T015 actually run before T017 if T017 depends on the file T015 creates? Are parallel markers (`[P]`) correct?

4. **Contract completeness:** Does every API endpoint have request/response schemas? Are error responses defined?

5. **Naming consistency:** Is it `answer_mode` everywhere, or is it `answerMode` in the frontend spec and `answer_mode` in the backend spec?

### How to run it

```
1. Load spec.md, plan.md, tasks.md (and contracts/ if they exist)
2. For each finding, classify severity:
   - HIGH: Will cause a runtime bug or blocked implementation
   - MEDIUM: Will cause confusion or rework
   - LOW: Style or documentation issue
3. Fix all HIGH findings before implementation
4. Fix MEDIUM findings if they touch code paths you're about to implement
5. Note LOW findings but don't block on them
```

## Anti-patterns (what NOT to do)

- **Generating tasks and implementing immediately.** In this project, `specs/001-foundation-setup/tasks.md` was modified in 4 of 9 total commits (3556ec5, 08aa62d, a4ba53d, 5543df1). The first version had wrong prerequisites, no user-story mapping, and incorrect parallel markers. Each fix commit was a rework that could have been avoided by running analysis before implementation.
- **Treating analysis as optional because "we'll catch it in code review."** The analysis step in this project found 8 findings in the foundation spec and 4 in the LangGraph agent spec. These included missing edge cases (what happens when GroundX returns empty results?), inconsistent field names, and incorrect dependency ordering. Finding these in code review means the code is already written — finding them in analysis means the code is never written wrong.
- **Running analysis once and never again.** The spec evolved through the clarify step (commit 02108ec added data model and API contracts). The analysis should run after every significant spec change, not just once.

## Example prompt or code template

```markdown
## Analysis Checklist (run before implementing)

### Cross-artifact consistency
- [ ] All field names match between spec.md and contracts/api.md
- [ ] All entities in data-model.md are referenced in plan.md
- [ ] All API endpoints in contracts/ have corresponding tasks in tasks.md
- [ ] Error response schemas are defined for every endpoint

### Edge cases
- [ ] Null/empty input behavior is specified for every field
- [ ] Backward compatibility is addressed (old clients, missing fields)
- [ ] Failure modes are defined (network error, model timeout, empty retrieval)

### Task dependencies
- [ ] No task depends on a file that hasn't been created yet
- [ ] Parallel markers [P] are correct (no shared state between parallel tasks)
- [ ] Phase ordering matches data flow (schema before routing before logic)

### Naming
- [ ] Consistent casing across backend (snake_case) and frontend (camelCase)
- [ ] No ambiguous abbreviations (does "mode" mean answer_mode or prompt_mode?)
```

## How we learned this

The project's git history tells the story:
- Commit 3556ec5: Created Phase 1 Foundation tasks
- Commit 08aa62d: Fixed parallel markers and Windows compatibility
- Commit a4ba53d: Resolved all 8 spec analysis findings (restructured tasks.md from 132 to 220 lines, reorganized by user story)
- Commit 5543df1: Resolved remaining review findings

The speckit-analyze skill (`.claude/skills/speckit-analyze/SKILL.md`) formalized this as part of the SDD workflow. The LangGraph agent spec (commit ba0696b) also needed 4 low-priority findings resolved after analysis. Every spec that was analyzed before implementation had fewer implementation bugs than specs that were implemented immediately.

## Reusability

Applies to any project using:
- Spec-driven or contract-first development
- AI-generated code from specifications
- Multi-component systems where contracts must align
- Iterative development where specs evolve alongside code

Particularly relevant for: AI-assisted development workflows, monorepo projects with shared contracts, API-first design, microservices with shared schemas.
