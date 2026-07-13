# ShiftMem Phase 2 Agent and Memory Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans and superpowers:test-driven-development.

**Goal:** Build and verify the offline structured Agent and five memory-baseline pipeline.

### Task 1: Schemas and provider abstraction

- [ ] Add Pydantic and write failing validation tests for decisions and provider responses.
- [ ] Implement structured schemas and provider protocol.
- [ ] Implement deterministic and scripted local providers for offline testing.

### Task 2: Common memory interface and baselines

- [ ] Write failing tests for common budgets and baseline retrieval behavior.
- [ ] Implement NoMemory, FullHistory, Summary, lexical Vector, and TimeDecay stores.
- [ ] Verify retrieval determinism and top-k limits.

### Task 3: Structured Agent retry and fallback

- [ ] Write failing tests for valid output, retry, double failure, memory-ID validation, and logging.
- [ ] Implement prompt construction, parsing, retry, fallback, and decision logs.
- [ ] Verify ordinary observations remain free of hidden state.

### Task 4: Baseline-switching CLI

- [ ] Write an integration test that runs all five baselines on one short episode.
- [ ] Implement `scripts/run_agent_episode.py` with memory-baseline selection.
- [ ] Emit JSON summary and auditable decision log without network access.

### Task 5: Verification

- [ ] Run all tests and compilation.
- [ ] Execute each baseline with the deterministic provider.
- [ ] Record limitations and decisions in `docs/implementation_log.md`.
