# ShiftMem Phase 2 Agent and Memory Baseline Design

## Scope

Implement a model-independent structured Agent pipeline and five memory baselines: NoMemory, FullHistory, Summary, Vector, and TimeDecay. Validate the complete flow offline with a deterministic provider. Do not implement ShiftMem lifecycle, change detection, remote APIs, or claim deterministic-provider runs as model results.

## Structured decision pipeline

All agents return a validated decision containing non-negative integer `order_quantity`, constant `supplier_id="standard"`, `used_memory_ids`, confidence in `[0,1]`, and a reason. A provider returns raw JSON plus token, latency, and failure metadata.

The agent builds the same observation schema and budgeted memory context for every baseline, requests JSON, validates it, retries once with a correction instruction, and then uses a classical fallback. Every attempt and final decision is logged.

## Memory baselines

- NoMemory: returns no historical context.
- FullHistory: returns the most recent records within a common item budget.
- Summary: returns a deterministic rolling natural-language summary of recent demand, sales, inventory, and lost sales.
- Vector: uses deterministic lexical cosine similarity to retrieve top-k records without an external embedding service.
- TimeDecay: combines lexical relevance with exponential time decay.

These stores expose the same `add(record)` and `retrieve(query, step, top_k)` interface. Retrieval IDs included in the prompt must match `used_memory_ids` in validated decisions.

## Offline provider

A deterministic local provider reads the observation embedded in the request and emits valid JSON using a transparent base-stock heuristic. It exists only for interface tests and short end-to-end runs. The provider abstraction keeps future local-model and compatible-API integrations replaceable.

## Validation

- All five baselines can be selected by one CLI flag.
- Invalid JSON triggers exactly one retry; a second failure uses fallback.
- Decisions cannot reference memory IDs absent from supplied context.
- Token, latency, retry, parse failure, raw output, and fallback use are logged.
- Same seed and provider produce identical episode logs.
- No network access or secret is required.
