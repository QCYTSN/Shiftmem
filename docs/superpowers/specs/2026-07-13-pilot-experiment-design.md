# ShiftMem Pilot Experiment Layer Design

## Scope

Build the classical-baseline pilot experiment layer before any ShiftMem or LLM work. The pilot runs paired policy comparisons on identical demand trajectories, writes auditable raw JSONL records, aggregates reproducible CSV summaries, and reports shift-segment metrics.

## Experiment matrix

- Scenarios: stable, sudden demand, gradual demand, periodic/combined, and supply delay.
- Policies: fixed, random, moving average, exponential smoothing, and Oracle.
- Seeds: 10 pilot seeds by default; configurable, never fewer than 5 in the committed pilot config.
- Horizon: 150 days.
- Split: all initial scenarios are marked `development`; validation and test/OOD configs will be frozen later.

## Fairness and random streams

Each run derives independent demand, supply, and policy streams from the same master seed. Every policy in a scenario receives the same demand seed. Policy actions must not change future demand samples, including when supply fill is stochastic.

## Outputs

`scripts/run_experiment.py` reads a YAML experiment config and writes one JSON object per scenario-policy-seed run. Each object contains identifiers, complete summary metrics, shift metadata, and daily records for audit and paired analysis.

`scripts/aggregate_results.py` groups raw runs by scenario and policy and writes CSV rows containing count, mean, sample standard deviation, and normal-approximation 95% confidence interval for each numeric metric.

## Metrics

Episode summaries include total and component costs, demand, sales, lost sales, service/fill rate, stockout rate, and average inventory. Shift scenarios additionally report pre-shift cost and service level plus post-shift 7/14/30-day cost, lost sales, and service level. Paired Oracle regret is computed in aggregation from runs sharing scenario and seed.

## Validation

- Same scenario and master seed yield identical demand sequences across all policies.
- Changing policy seed does not change environment demand.
- CLI pilot produces the expected run count.
- Aggregation reports correct means, sample standard deviations, confidence intervals, and paired Oracle regret.
- Full test suite remains network-free and deterministic.
