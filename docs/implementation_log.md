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

## 2026-07-13 — Classical development pilot

- Added separate demand and supply RNG streams inside each environment so policy-dependent supply sampling cannot alter paired demand trajectories.
- Fixed the development pilot at five scenarios, five classical policies, ten paired seeds, and 150-day episodes.
- Added average inventory, stockout-day rate, fill rate, and pre/post-shift 7/14/30-day metrics.
- Stored raw run records as ignored JSONL under `artifacts/raw_runs/` and committed aggregate CSV outputs under `artifacts/aggregated/`.
- Used sample standard deviation and a normal-approximation 95% confidence interval for pilot summaries. Formal analysis may replace the approximation after power and distribution checks.
- Calculated total-cost regret by pairing each policy with Oracle on the same scenario and master seed.
- Classified all current pilot scenarios as development data; validation, Test-ID, and Test-OOD remain unfrozen.

## 2026-07-13 — Phase 2 offline Agent foundation

- Added Pydantic-validated Agent decisions and provider request/response schemas.
- Standardized provider parsing to one initial attempt, one correction retry, then a classical safe fallback.
- Logged raw outputs, token counts, latency, parse failures, supplied memory IDs, final decisions, and fallback use.
- Added NoMemory, bounded FullHistory, deterministic Summary, lexical Vector, and lexical-plus-time-decay memory baselines behind one interface.
- Rejected any decision that cites a memory ID not supplied in its retrieval context.
- Added a deterministic provider and baseline-switching CLI for offline integration only. It deliberately ignores memory content, so these runs must not be interpreted as memory-method comparisons.
- Deferred a real local instruction model and compatible API integration until hardware, model license, and model selection are explicitly decided.

## 2026-07-13 — CPU-only compatible provider

- Detected an Intel Core Ultra 5 125H and 31.5 GB system memory with no Ollama, llama.cpp, or GPU runtime installed.
- Kept deterministic mode as the offline default and added an opt-in OpenAI-compatible chat-completions provider.
- Loaded endpoint, model name, and API key only from the process environment or ignored local `.env`; credentials are represented as secret values and omitted from errors and logs.
- Injected the HTTP transport so all automated tests remain offline and deterministic.
- Added sanitized handling for HTTP status, connection, timeout, malformed envelope, provider exception, JSON parse, and decision validation failures.
- Deferred the first real model smoke test until the user configures a compatible endpoint. No model choice or provider-specific result has been recorded.

## 2026-07-13 — Named remote model profiles

- Added independent Bailian and SiliconFlow profiles over the same OpenAI-compatible transport; only the selected profile's key is required.
- Fixed non-thinking JSON generation defaults at temperature 0, 512 maximum output tokens, and a 60-second timeout.
- Selected `qwen3.5-flash-2026-02-23` as the low-cost pinned Bailian smoke model and `deepseek-ai/DeepSeek-V3.2` as the default SiliconFlow cross-family model.
- Kept `qwen3.7-plus-2026-05-26`, `Pro/zai-org/GLM-4.7`, and `Pro/zai-org/GLM-5.1` as explicit per-run overrides.
- Kept deterministic mode as the CLI default and did not perform a live request before the user supplied a key and reviewed provider billing and quotas.
