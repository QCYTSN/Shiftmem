# ShiftMem Phase 1 Environment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic lost-sales inventory environment, synthetic regime scenarios, classical baselines, a no-LLM episode runner, and a validation figure.

**Architecture:** Use immutable validated dataclasses for scenario parameters, NumPy generators for all stochastic behavior, and a lightweight Gymnasium-shaped environment interface. Keep scenario generation, environment transitions, policies, metrics, plotting, and CLI orchestration independently testable.

**Tech Stack:** Python 3.12+, NumPy, PyYAML, Matplotlib, pytest, setuptools.

## Global Constraints

- Default mode is lost sales; inventory may not become negative.
- Default episode length is 150 days.
- The only Phase 1 supplier ID is `standard`, but actions retain `supplier_id`.
- Reward is the negative of purchase, holding, stockout, and fixed-ordering costs.
- Identical configuration, policy parameters, and random seed must reproduce the complete trajectory.
- No external datasets, network calls, real model provider, ShiftMem implementation, detector implementation, or Demo work.
- Hidden regime state and future demand must never enter ordinary agent observations.
- Record implementation decisions and deviations in `docs/implementation_log.md`.

---

### Task 1: Development dependencies and deterministic demand models

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/unit/test_demand_models.py`
- Modify: `src/shiftmem/envs/demand_models.py`

**Interfaces:**
- Produces: `DemandParameters`, `PoissonDemand`, and `NegativeBinomialDemand`, each exposing `sample(rng, parameters) -> int`.

- [ ] **Step 1: Configure runtime and test dependencies**

Add NumPy, PyYAML, and Matplotlib runtime dependencies plus a `test` optional dependency containing pytest. Configure pytest with `pythonpath = ["src"]` and `testpaths = ["tests"]`.

- [ ] **Step 2: Write demand-model tests**

Test that `DemandParameters.mean` equals `base_level * seasonal_factor * promotion_factor * external_factor`, invalid non-positive parameters raise `ValueError`, same-seed sampling is identical, samples are non-negative integers, and a large negative-binomial sample has variance greater than its mean.

- [ ] **Step 3: Run tests and verify the red state**

Run `python -m pytest tests/unit/test_demand_models.py -v` and expect import failures for the unimplemented demand types.

- [ ] **Step 4: Implement demand models**

Use frozen dataclasses. Parameterize NumPy negative binomial with `n=dispersion` and `p=dispersion/(dispersion+mean)`. Accept only a caller-supplied `numpy.random.Generator`.

- [ ] **Step 5: Run focused tests**

Run `python -m pytest tests/unit/test_demand_models.py -v` and expect all demand tests to pass.

### Task 2: Regime schedules, supply model, and YAML scenarios

**Files:**
- Create: `tests/unit/test_shifts.py`
- Create: `tests/unit/test_supply_models.py`
- Modify: `src/shiftmem/envs/shifts.py`
- Modify: `src/shiftmem/envs/supply_models.py`
- Create: `configs/environments/stable.yaml`
- Create: `configs/environments/demand_jump.yaml`
- Create: `configs/environments/supply_delay.yaml`

**Interfaces:**
- Consumes: `DemandParameters` from Task 1.
- Produces: validated `Scenario`, `CostParameters`, `SupplyParameters`, `load_scenario(path)`, `Scenario.parameters_at(day)`, and `SingleSupplier.arrival_quantity(order_quantity, rng, parameters)`.

- [ ] **Step 1: Write schedule and supply tests**

Cover stable, sudden, gradual, periodic, supply, combined, and false-alarm schedules at boundary days. Test YAML loading, invalid episode length, invalid shift ranges, supplier validation, non-negative order validation, fixed lead time, and fill-rate reproducibility.

- [ ] **Step 2: Run tests and verify the red state**

Run `python -m pytest tests/unit/test_shifts.py tests/unit/test_supply_models.py -v` and expect missing-interface failures.

- [ ] **Step 3: Implement scenario types and loader**

Represent shifts as validated mappings with explicit `type`, `start_day`, `end_day`, and parameter changes. `parameters_at(day)` must return current demand and supply dataclasses without mutating base configuration. Reject unsupported keys and shift types.

- [ ] **Step 4: Implement the supplier model**

For `fill_rate == 1.0`, arrival equals the submitted integer quantity. Otherwise sample arrived units with `rng.binomial(order_quantity, fill_rate)`. Lead time is supplied by the current scenario parameters and must be at least one day.

- [ ] **Step 5: Add three runnable YAML scenarios**

Each file specifies seed-independent parameters, 150-day horizon, initial inventory, demand model, base demand and supply parameters, costs, and shifts. Use stable demand, a day-75 demand mean increase, and a day-75 lead-time increase respectively.

- [ ] **Step 6: Run focused tests**

Run `python -m pytest tests/unit/test_shifts.py tests/unit/test_supply_models.py -v` and expect all tests to pass.

### Task 3: Lost-sales inventory environment

**Files:**
- Create: `tests/unit/test_inventory_env.py`
- Modify: `src/shiftmem/envs/inventory_env.py`
- Modify: `src/shiftmem/envs/__init__.py`

**Interfaces:**
- Consumes: `Scenario`, demand models, and `SingleSupplier`.
- Produces: `InventoryEnv.reset(seed=None) -> tuple[dict, dict]`, `InventoryEnv.step(action) -> tuple[dict, float, bool, bool, dict]`, and read-only `InventoryEnv.oracle_context()`.

- [ ] **Step 1: Write environment transition tests**

Use deterministic demand fixtures to test reset, action validation, arrival timing, daily inventory conservation, lost-sales non-negativity, cost decomposition, reward sign, termination at day 150, seed reproducibility, and absence of hidden keys from observations.

- [ ] **Step 2: Run tests and verify the red state**

Run `python -m pytest tests/unit/test_inventory_env.py -v` and expect missing-environment failures.

- [ ] **Step 3: Implement reset and observable state**

Reset the RNG and all episode state, pending orders, histories, and totals. Observation keys are `day`, `inventory`, `pipeline_inventory`, `last_demand`, and `last_sales` only.

- [ ] **Step 4: Implement step transitions**

Process arrivals, sample demand from current regime, calculate sales and lost sales, validate and schedule the new order, calculate cost fields, append an auditable record, and advance the day. Return `terminated=True` after the configured horizon and keep `truncated=False`.

- [ ] **Step 5: Expose isolated oracle context**

Return only the current true demand mean, lead time, and fill rate through `oracle_context()`. Do not merge this data into observations or ordinary `info`.

- [ ] **Step 6: Run focused and cumulative tests**

Run `python -m pytest tests/unit/test_inventory_env.py -v`, then `python -m pytest tests/unit -v`; expect all tests to pass.

### Task 4: Classical policies and fairness sanity check

**Files:**
- Create: `tests/unit/test_classical_agents.py`
- Modify: `src/shiftmem/agents/classical.py`
- Modify: `src/shiftmem/agents/__init__.py`

**Interfaces:**
- Consumes: ordinary environment observations; Oracle additionally consumes explicit oracle context.
- Produces: `FixedOrderPolicy`, `RandomOrderPolicy`, `MovingAverageReorderPolicy`, `ExponentialSmoothingPolicy`, and `OraclePolicy`, each returning `{"order_quantity": int, "supplier_id": "standard"}`.

- [ ] **Step 1: Write policy tests**

Test legal action shape, seeded random reproducibility, moving-window updates, exponential-smoothing updates, non-negative orders, pipeline-aware inventory position, and rejection of malformed observations.

- [ ] **Step 2: Write Oracle sanity test**

Across a fixed seed set in a simplified stable scenario, compare total costs and assert Oracle mean cost is lower than random-policy mean cost. Ordinary policies must not receive oracle context.

- [ ] **Step 3: Run tests and verify the red state**

Run `python -m pytest tests/unit/test_classical_agents.py -v` and expect missing-policy failures.

- [ ] **Step 4: Implement policies**

Use explicit constructor validation and local RNG ownership for the random policy. Base-stock calculations must subtract both on-hand and pipeline inventory and clamp order quantity to zero or greater.

- [ ] **Step 5: Run focused and cumulative tests**

Run `python -m pytest tests/unit/test_classical_agents.py -v`, then `python -m pytest tests/unit -v`; expect all tests to pass.

### Task 5: Metrics, runner, validation plot, and integration test

**Files:**
- Create: `tests/integration/test_run_episode.py`
- Modify: `src/shiftmem/evaluation/metrics.py`
- Modify: `src/shiftmem/evaluation/plots.py`
- Modify: `scripts/run_episode.py`
- Modify: `docs/implementation_log.md`

**Interfaces:**
- Consumes: scenario YAML, policy name and parameters, environment records.
- Produces: `summarize_episode(records) -> dict`, `plot_episode(records, output_path) -> Path`, and a CLI that prints JSON summary and optionally writes a PNG.

- [ ] **Step 1: Write integration test**

Run the CLI as a subprocess against `configs/environments/stable.yaml` with a fixed-order policy and seed 42. Assert exit code 0, valid JSON summary, `days == 150`, finite non-negative total cost, service level in `[0, 1]`, and a non-empty PNG output.

- [ ] **Step 2: Run integration test and verify the red state**

Run `python -m pytest tests/integration/test_run_episode.py -v` and expect failure because orchestration is not implemented.

- [ ] **Step 3: Implement metrics and plot**

Summarize total demand, sales, lost sales, total and component costs, and service level. Plot demand/sales, inventory/pipeline, orders/arrivals, and daily cost in four aligned panels and close the Matplotlib figure after saving.

- [ ] **Step 4: Implement the CLI**

Support `--config`, `--policy`, `--seed`, `--order-quantity`, and `--figure`. Instantiate only classical policies, run until termination, print the summary as JSON, and never access network or provider modules.

- [ ] **Step 5: Record implementation decisions**

Append the chosen event order, purchase-cost timing, observation keys, dependency choices, default horizon, lost-sales mode, and any actual deviations to `docs/implementation_log.md`.

- [ ] **Step 6: Run the full verification suite**

Run:

```powershell
python -m pytest -v
python -m compileall -q src scripts
python scripts/run_episode.py --config configs/environments/demand_jump.yaml --policy fixed --order-quantity 20 --seed 42 --figure artifacts/figures/phase1_validation.png
```

Expected: all tests pass, compilation exits 0, the CLI reports a 150-day summary, and `artifacts/figures/phase1_validation.png` is non-empty.

