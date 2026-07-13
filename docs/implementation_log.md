# Implementation Log

Implementation decisions and deviations from the specification will be recorded here as development proceeds.

## 2026-07-13 — Phase 1 environment foundation

- Selected Python 3.12+, NumPy, PyYAML, Matplotlib, and pytest with a lightweight Gymnasium-shaped interface.
- Fixed the default environment to lost sales with a 150-day horizon and one `standard` supplier.
- Fixed daily event order to arrivals, regime lookup, demand sampling, sales/lost sales, new-order scheduling, cost calculation, then day advancement.
- Recognize purchase cost on the order day; recognize holding and stockout costs after demand is realized.
- Restricted ordinary observations to day, on-hand inventory, pipeline inventory, last demand, and last sales.
- Kept true demand mean, lead time, and fill rate in an explicit Oracle-only context.
- Added two protection-period standard deviations of safety stock to the simplified Oracle after its mean-only base-stock rule failed the required random-policy sanity comparison.
- Used synthetic scenarios only; no external data or model API is required in Phase 1.

## 2026-07-13 — Phase 1 diagnostic corrections

- Deferred stochastic fill-rate sampling until the order arrival day. Pipeline inventory now reports the nominal outstanding order quantity rather than revealing the future realized fill.
- Extended Oracle-only context with demand-model type and dispersion. Oracle safety stock now uses the configured Poisson or negative-binomial variance.
- Derived independent reproducible environment and policy RNG seeds from the CLI master seed.
- Added regime-shift markers to generated diagnostic figures.
- Retained fixed-order policy as an intentionally weak sanity baseline; multi-seed aggregation remains a separate evaluation task.
