# Inventory Observation, Prompt, and Model Qualification Design

## Goal

Qualify language models for ShiftMem's inventory-control task before freezing the formal experiment models. Qualification must test task behavior rather than merely API connectivity or JSON syntax, and it must not use main-experiment outcomes to select a model.

## Scope and ordering

This work has three sequential parts:

1. bring the public Agent observation up to the implementation specification;
2. define one provider-independent inventory decision instruction;
3. run a small, pre-main-experiment model qualification suite.

No ShiftMem effectiveness claim, hyperparameter search, large episode matrix, or main-test scenario is included.

## Public observation

Every Agent and memory baseline receives the same public observation. It contains only information an inventory manager could know at decision time:

```json
{
  "day": 14,
  "inventory": 37,
  "pipeline_inventory": 40,
  "pipeline_orders": [
    {"due_day": 15, "quantity": 20},
    {"due_day": 16, "quantity": 20}
  ],
  "quoted_lead_time": 2,
  "last_demand": 24,
  "last_sales": 24,
  "costs": {
    "purchase": 1.0,
    "holding": 0.2,
    "stockout": 5.0,
    "fixed_order": 0.0
  },
  "recent_history": [
    {
      "day": 13,
      "demand": 24,
      "sales": 24,
      "lost_sales": 0,
      "ending_inventory": 37,
      "order_quantity": 20,
      "arrivals": 0,
      "total_cost": 27.4
    }
  ]
}
```

`recent_history` is a chronological rolling window of at most 14 completed days. `pipeline_orders` reports nominal outstanding quantities and known due days; it never reveals future realized fill. `quoted_lead_time` is the supplier term used for an order placed on the current day. Costs are public scenario constants.

The observation must not contain the demand distribution parameters, dispersion, future demand, future realized fill, shift schedule, hidden regime identifier, or Oracle context.

The environment observation type broadens from `dict[str, int]` to `dict[str, Any]`. Existing scalar keys remain unchanged for backward compatibility.

## Unified decision instruction

The provider system instruction is model- and provider-independent. It tells the frozen model to act as a single-item lost-sales inventory manager and to minimize total purchase, holding, stockout, and fixed ordering costs over time.

The instruction defines the observable fields and requires the model to:

- account for on-hand and all pipeline inventory before ordering;
- use recent realized history to estimate direction and variability without assuming hidden parameters;
- avoid duplicate replenishment when scheduled arrivals already cover near-term demand;
- raise protection when recent lost sales or demand increase and reduce it when inventory and pipeline are excessive;
- treat retrieved memories as fallible evidence, use only records applicable to the current public state, and cite only supplied IDs actually used;
- return one JSON object matching `AgentDecision`, with no extra fields.

The prompt does not prescribe a base-stock formula or expose Oracle information. That leaves room for memory methods to affect reasoning while giving every model the same task objective and constraints.

Correction retries repeat the inventory objective and identify only the validation problem. They never add hidden information or a model-specific hint.

## Qualification candidates

The initial roles are fixed before qualification:

- development control: Bailian `qwen3.5-flash-2026-02-23`;
- formal open-weight candidate A: SiliconFlow `Qwen/Qwen3.5-35B-A3B` (Apache-2.0);
- formal open-weight candidate B: SiliconFlow `deepseek-ai/DeepSeek-V3.2` (MIT);
- supplementary open-weight candidate: SiliconFlow `Pro/zai-org/GLM-5.1` (MIT);
- optional commercial upper bound after core experiments: Bailian `qwen3.7-plus-2026-05-26`.

Using one SiliconFlow endpoint for the three open-weight candidates reduces provider-level confounding during model-family qualification. Exact provider model IDs and the qualification date are recorded with results.

## Qualification cases

Qualification uses synthetic public observations that are separate from frozen main-test scenarios. Cases form paired behavioral checks:

1. **Demand monotonicity:** with other fields fixed, sustained higher recent demand must not produce a lower order than sustained lower demand.
2. **Pipeline sensitivity:** with other fields fixed, a large near-term pipeline must not produce a larger order than an empty pipeline.
3. **Stockout-cost sensitivity:** with other fields fixed, a higher stockout penalty must not produce a lower order than a low penalty.
4. **Applicable memory:** a supplied active memory consistent with recent observations may affect the decision and must be cited if used.
5. **Inapplicable memory:** a dormant or explicitly mismatched memory must not be cited.
6. **Safety and schema:** quantity is a non-negative integer, supplier is `standard`, confidence is bounded, reason is non-empty, and no unsupplied memory ID appears.

Each candidate receives the same serialized requests at temperature 0 and non-thinking JSON mode. Each case is repeated twice to reveal provider nondeterminism without creating a large bill.

## Qualification metrics and gates

The runner records raw decision JSON, parsed decisions, failures, retries, input/output tokens, and latency in ignored raw artifacts. A compact aggregate JSON is trackable.

A formal candidate qualifies only if it meets every hard gate:

- 100% parseable `AgentDecision` output after the existing single retry;
- 0 fallback decisions;
- 0 unsupplied-memory citations;
- 0 citations of the explicitly inapplicable memory;
- all three paired monotonicity checks pass on both repetitions.

Latency, token use, order dispersion, applicable-memory citation, and exact repeated-decision agreement are diagnostic metrics, not hard gates. A model that fails a hard gate is excluded or retested only after a provider-independent prompt correction applied equally to all candidates.

The development Flash model is reported but is not eligible to support the paper's core conclusions. GLM-5.1 remains supplementary even if it passes because of cost. At least the Qwen open-weight and DeepSeek candidates must pass before the two-model formal design is frozen; otherwise model selection remains unresolved.

## Components

- `InventoryEnv` builds the richer public observation and owns the 14-day rolling window.
- A focused prompt module owns the unified instruction and deterministic request serialization.
- A pure qualification evaluator defines cases and computes gates from decisions without network access.
- A CLI resolves configured provider profiles, runs the small live suite, writes ignored raw JSONL plus a compact aggregate result, and never prints credentials or raw authorization data.

Provider transport, retry/fallback, memory implementations, environment transition dynamics, and classical policies remain unchanged.

## Testing and safety

TDD covers observation contents, 14-day truncation and chronology, absence of hidden fields, prompt requirements, paired gate calculations, failure accounting, deterministic case generation, model metadata, and output paths. HTTP is faked in automated tests.

Before live qualification, the runner verifies that each exact model ID exists in the selected account. A missing or incompatible model is recorded as unavailable rather than silently substituted. Live qualification requires already configured ignored `.env` credentials and uses only the bounded case matrix above.

Completion requires the full offline test suite, compilation, diff checks, ignored-artifact checks, populated-key scans, and a human-readable qualification summary that clearly separates interface success from task suitability.
