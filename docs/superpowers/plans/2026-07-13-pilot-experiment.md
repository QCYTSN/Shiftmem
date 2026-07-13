# ShiftMem Pilot Experiment Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox syntax for tracking.

**Goal:** Add fair multi-seed classical pilot execution and aggregation.

**Architecture:** Separate stochastic streams inside the environment, run a YAML-defined scenario-policy-seed matrix, persist JSONL audit records, and aggregate paired metrics to CSV using the standard library.

**Tech Stack:** Python 3.12+, NumPy, PyYAML, pytest, CSV/JSON standard library.

### Task 1: Fair environment random streams

- [ ] Add a failing test proving different order actions do not alter demand trajectories under stochastic fill.
- [ ] Derive independent demand and supply generators during environment reset.
- [ ] Run environment and policy regression tests.

### Task 2: Complete pilot scenarios and metrics

- [ ] Add failing tests for stockout rate, average inventory, and 7/14/30-day shift segments.
- [ ] Extend `summarize_episode(records, shift_day=None)`.
- [ ] Add gradual and periodic/combined YAML scenarios.
- [ ] Add a ten-seed development pilot YAML.

### Task 3: Multi-run experiment CLI

- [ ] Add an integration test for exact matrix size and paired demand trajectories.
- [ ] Implement `scripts/run_experiment.py` with JSONL output.
- [ ] Verify no provider or network module is imported.

### Task 4: Aggregation CLI

- [ ] Add tests for means, sample standard deviations, 95% confidence intervals, and paired Oracle regret.
- [ ] Implement `scripts/aggregate_results.py` with CSV output.
- [ ] Run a small pilot fixture and validate its artifacts.

### Task 5: Full verification

- [ ] Run all tests and Python compilation.
- [ ] Run the committed pilot configuration.
- [ ] Aggregate the results and inspect run counts and metric ranges.
- [ ] Record decisions in `docs/implementation_log.md`.
