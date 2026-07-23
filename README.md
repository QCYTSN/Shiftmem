# ShiftMem

Change-aware conditional memory for inventory agents under regime shifts.

ShiftMem is a research project investigating whether condition-aware memory can help inventory agents adapt when demand or supply regimes change. In the v2 architecture, an LLM performs bounded strategy review every five days or after a detected change, while a shared deterministic controller computes exact daily orders. This separates memory-assisted adaptation from high-frequency arithmetic and output noise.

The authoritative project scope, research questions, experimental design, and phased implementation requirements are documented in [ShiftMem_Implementation_Spec.md](ShiftMem_Implementation_Spec.md).

## Planned structure

- `src/shiftmem/envs/`: inventory environment, demand, supply, and shift models
- `src/shiftmem/agents/`: shared agent interfaces and baselines
- `src/shiftmem/memory/`: ShiftMem schemas, storage, retrieval, validation, and lifecycle
- `src/shiftmem/detection/`: online regime-change detectors
- `src/shiftmem/evaluation/`: metrics, statistics, and plots
- `src/shiftmem/providers/`: model-provider abstractions
- `configs/`, `scripts/`, and `tests/`: reproducible configuration, entry points, and verification
- `artifacts/`: raw, aggregated, and figure outputs with different tracking policies

## Credentials

Copy `.env.example` to `.env` for local configuration. Keep `.env` local and never commit API keys or other credentials. The repository template contains variable names only and no secret values.

## Classical pilot

Run the network-free development pilot and aggregate its results with:

```powershell
python scripts/run_experiment.py --config configs/experiments/classical_pilot.yaml --output artifacts/raw_runs/classical_pilot.jsonl
python scripts/aggregate_results.py --input artifacts/raw_runs/classical_pilot.jsonl --output artifacts/aggregated/classical_pilot_summary.csv
```

The committed pilot contains five synthetic scenarios, five classical policies, and ten paired environment seeds. Raw daily records are ignored by Git; aggregate CSV results remain trackable.

## Offline Agent pipeline

Validate the structured Agent, retry/fallback, decision logging, and a selected memory baseline without a model or network connection:

```powershell
python scripts/run_agent_episode.py --config configs/environments/stable.yaml --memory vector --seed 42 --output artifacts/raw_runs/vector_agent.json
```

Available offline memory baselines are `none`, `full_history`, `summary`, `vector`, and `time_decay`. The deterministic provider validates interfaces only; its output is not a model-performance result.

The Phase 3 deterministic ShiftMem loop is also available offline:

```powershell
.venv\Scripts\python.exe scripts/run_agent_episode.py --config configs/environments/stable.yaml --memory shiftmem --provider deterministic --max-days 30 --output artifacts/raw_runs/shiftmem_offline.json
```

This path extracts delayed decision experiences, monitors public demand and lost-sales signals with Page-Hinkley, updates Beta-Bernoulli confidence and lifecycle state, and performs condition-aware retrieval. Its default semantic component is lexical cosine so development and tests require neither a GPU nor an embedding API. The current detector thresholds, lifecycle thresholds, and retrieval weights are development defaults that must be selected on validation scenarios before formal tests. A deterministic-provider run verifies integration and auditability only; it is not evidence that ShiftMem improves inventory performance.

The local `.env` is preconfigured for Alibaba Cloud Model Studio (Bailian) and SiliconFlow. Fill only the matching blank API key, then select the provider explicitly. The CLI remains deterministic by default so an ordinary offline command cannot spend API credit accidentally.

```powershell
python scripts/run_agent_episode.py --config configs/environments/stable.yaml --memory vector --provider bailian --max-days 10 --output artifacts/raw_runs/bailian_smoke.json
python scripts/run_agent_episode.py --config configs/environments/stable.yaml --memory vector --provider siliconflow --model-name Pro/zai-org/GLM-5.1 --max-days 10 --output artifacts/raw_runs/siliconflow_glm_smoke.json
```

The configured defaults are the version-pinned `qwen3.5-flash-2026-02-23` for low-cost Bailian smoke tests and `deepseek-ai/DeepSeek-V3.2` for SiliconFlow comparisons. Use `--model-name qwen3.7-plus-2026-05-26` only for an explicitly designed commercial upper-bound run. Never commit `.env`, and do not make a live call until the selected key is filled and the account's billing and quota settings have been checked.

## Inventory model qualification

Run the fixed eight-case, two-repetition qualification matrix with:

```powershell
.venv\Scripts\python.exe scripts/qualify_models.py --config configs/experiments/model_qualification.yaml --raw-output artifacts/raw_runs/model_qualification.jsonl --summary-output artifacts/aggregated/model_qualification_summary.json
```

The 2026-07-13 qualification and second-core gate selected `deepseek-ai/DeepSeek-V3.2` as Core A and `MiniMaxAI/MiniMax-M2.5` as Core B. `Pro/zai-org/GLM-5.1` remains supplementary. Both tested Qwen candidates produced valid, monotonic decisions but cited an explicitly dormant, mismatched memory in both repetitions and therefore failed the fixed applicability gate. See [the qualification report](docs/model_qualification.md) and the trackable [aggregate JSON](artifacts/aggregated/model_qualification_summary.json).

## Research freeze and current readiness

The Phase 4 v1 audit snapshot is `phase4-20260713-b99c0d3e4d27`. It preserves the protocol, split manifests, selected Validation settings, qualified core models, and bounded Pilot evidence as they stood at the freeze. Verify it without network access:

```powershell
.venv\Scripts\python.exe scripts/verify_freeze.py configs/frozen/phase4-20260713-b99c0d3e4d27
.venv\Scripts\python.exe -m pytest -q
```

The v1 snapshot is verified but was **never authorized for formal Test execution**. A post-freeze audit found a detector-selection/runtime signal mismatch, missing held-out stable and periodic coverage for H3/H4, incomplete formal statistics and result logging, and insufficiently idempotent live-run recovery. Protocol v1.1 engineering corrected those implementation blockers and completed a CNY 3.2184 Validation-only dry-run, but its direct-daily-order matrix was not frozen or run on held-out outcomes.

Protocol v2 is implemented and its paid held-out matrix completed on 2026-07-22. The LLM proposes a bounded strategy vector at five-day reviews or detector events, while a deterministic controller executes every daily order. The final Amendment 1 matrix contains VectorMemory versus ShiftMem across two core models, eight held-out scenarios, and five paired seeds: 80 Test-ID plus 80 Test-OOD cells. No paid secondary tier was run.

The immutable raw Test inputs remain byte-for-byte unchanged. The current post-Test closure identity is `v2-formal-results-b70e28f0fa8c`; it supersedes the first closure analysis identity after adding post-hoc clustered-mean and execution-order sensitivity analyses. Reproduce and verify the machine-readable evidence, statistics, and reliability outputs without making a provider call:

```powershell
.venv\Scripts\python.exe scripts/finalize_formal_results.py --verify
```

The archived v1 package remains immutable. The v1.1 CNY 1,506.22 projection and proposed CNY 1,810 cap are retired historical estimates, not v2 costs. See the [post-Test audit](docs/v2_formal_post_test_audit.md), [v2 protocol](docs/experiment_protocol.md), and historical [v1.1 Validation report](docs/v1_1_live_validation_report.md).

## License

No license has been selected yet.
