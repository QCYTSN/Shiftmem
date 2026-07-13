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

## License

No license has been selected yet.
