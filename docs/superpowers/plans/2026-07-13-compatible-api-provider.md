# Compatible API Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans and superpowers:test-driven-development.

**Goal:** Add a secure, offline-tested compatible API provider and wire it into the Agent CLI.

### Task 1: Configuration and transport

- [ ] Add python-dotenv and failing tests for environment loading, URL normalization, and secret redaction.
- [ ] Implement provider configuration, transport protocol, urllib transport, and sanitized provider errors.

### Task 2: Chat-completions provider

- [ ] Add failing tests for request JSON, authorization, response extraction, usage, and failure envelopes.
- [ ] Implement `CompatibleAPIProvider.generate` without changing `StructuredAgent`.

### Task 3: CLI selection and fallback integration

- [ ] Add tests for deterministic default and compatible-provider construction.
- [ ] Add `--provider deterministic|compatible` to `run_agent_episode.py`.
- [ ] Keep all CI and test execution network-free.

### Task 4: Verification and documentation

- [ ] Run full tests and compilation.
- [ ] Verify secret scans and deterministic CLI.
- [ ] Document the CPU-only limitation and the user-supplied environment needed for the first real smoke test.
