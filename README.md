# ShiftMem

Change-aware conditional memory for inventory agents under regime shifts.

ShiftMem is a research project investigating whether condition-aware memory can help inventory agents adapt when demand or supply regimes change. The repository is currently at the scaffold stage: its package boundaries and research artifacts are defined, but the environment, agents, memory system, experiments, and demo are not yet implemented.

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

The local `.env` is preconfigured for Alibaba Cloud Model Studio (Bailian) and SiliconFlow. Fill only the matching blank API key, then select the provider explicitly. The CLI remains deterministic by default so an ordinary offline command cannot spend API credit accidentally.

```powershell
python scripts/run_agent_episode.py --config configs/environments/stable.yaml --memory vector --provider bailian --max-days 10 --output artifacts/raw_runs/bailian_smoke.json
python scripts/run_agent_episode.py --config configs/environments/stable.yaml --memory vector --provider siliconflow --model-name Pro/zai-org/GLM-4.7 --max-days 10 --output artifacts/raw_runs/siliconflow_glm_smoke.json
```

The configured defaults are the version-pinned `qwen3.5-flash-2026-02-23` for low-cost Bailian smoke tests and `deepseek-ai/DeepSeek-V3.2` for SiliconFlow comparisons. Use `--model-name qwen3.7-plus-2026-05-26` for a formal Qwen run. Never commit `.env`, and do not make a live call until the selected key is filled and the account's billing and quota settings have been checked.

## License

No license has been selected yet.
