"""Run the bounded Validation-only DeepSeek retrieval-weight pilot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any

import yaml

from shiftmem.agents.classical import FixedOrderPolicy, MovingAverageReorderPolicy
from shiftmem.agents.llm_agent import StructuredAgent
from shiftmem.envs.inventory_env import InventoryEnv
from shiftmem.envs.shifts import load_scenario
from shiftmem.memory.retriever import RetrievalWeights
from shiftmem.memory.schemas import ExperienceRecord, MemoryRecord, MemoryStatus
from shiftmem.memory.shiftmem import ShiftMemory, ShiftMemoryConfig
from shiftmem.memory.store import VectorMemory
from shiftmem.providers.compatible_api import CompatibleAPIProvider, ProviderConfig

try:
    from scripts.run_episode import derive_seeds
except ModuleNotFoundError:
    from run_episode import derive_seeds


def estimate_call_count(config: dict[str, Any]) -> int:
    return (
        (len(config["retrieval_grid"]) + 1)
        * len(config["seeds"])
        * int(config["post_shift_days"])
    )


def aggregate_rows(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    vector = {
        int(run["seed"]): float(run["cost"])
        for run in runs
        if run["config_id"] == "vector"
    }
    grouped: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        if run["config_id"] != "vector":
            grouped.setdefault(str(run["config_id"]), []).append(run)
    rows = []
    for config_id, group in sorted(grouped.items()):
        if any(int(run["seed"]) not in vector for run in group):
            raise ValueError(f"missing paired vector run for {config_id}")
        rows.append(
            {
                "config_id": config_id,
                "post_shift_cumulative_regret_30": mean(
                    float(run["cost"]) - vector[int(run["seed"])] for run in group
                ),
                "invalid_reuse": sum(int(run["invalid_reuse"]) for run in group),
                "tokens": sum(int(run["tokens"]) for run in group),
                "completed_runs": len(group),
            }
        )
    return rows


def _seed_memories(memory: ShiftMemory | VectorMemory) -> None:
    definitions = [
        ("m-protect", 10, "After a demand increase, raise protection inventory and avoid stockouts.", 9.0, 1.0, 0.9),
        ("m-recent", 70, "Recent demand should drive an adaptive order-up-to decision.", 2.0, 1.0, 0.6),
        ("m-pipeline", 55, "Subtract pipeline inventory before ordering to avoid excess stock.", 5.0, 1.0, 0.8),
        ("m-cost", 35, "Balance purchase, holding, and lost-sales costs in every order.", 4.0, 2.0, 0.7),
    ]
    for memory_id, step, text, alpha, beta, utility in definitions:
        if isinstance(memory, ShiftMemory):
            memory.import_experience(
                ExperienceRecord(
                    memory_id=memory_id,
                    created_step=step,
                    text=text,
                    variables=["demand", "inventory"],
                    status=MemoryStatus.ACTIVE,
                    alpha=alpha,
                    beta=beta,
                    utility=utility,
                )
            )
        else:
            memory.add(
                MemoryRecord(
                    memory_id=memory_id,
                    step=step,
                    text=text,
                    variables=["demand", "inventory"],
                )
            )


def _make_memory(run_config: dict[str, Any]):
    if run_config["config_id"] == "vector":
        memory = VectorMemory()
    else:
        weights = dict(run_config["weights"])
        weights.setdefault("recency_half_life", 30.0)
        memory = ShiftMemory(
            ShiftMemoryConfig(
                dormancy_patience=int(run_config["dormancy_patience"]),
                detector_min_samples=int(run_config.get("detector_min_samples", 10)),
                detector_delta=float(run_config.get("detector_delta", 0.05)),
                detector_threshold=float(run_config.get("detector_threshold", 5.0)),
            ),
            retrieval_weights=RetrievalWeights(**weights),
        )
    _seed_memories(memory)
    return memory


def run_one(
    scenario_path: Path,
    seed: int,
    post_shift_days: int,
    run_config: dict[str, Any],
    profile: str,
    model_id: str,
) -> dict[str, Any]:
    scenario = load_scenario(scenario_path)
    shift_days = [shift.start_day for shift in scenario.shifts if shift.start_day > 0]
    if not shift_days:
        raise ValueError("retrieval pilot requires a shifted Validation scenario")
    shift_day = min(shift_days)
    if shift_day + post_shift_days > scenario.episode_length:
        raise ValueError("post-shift window exceeds episode")
    environment_seed, _ = derive_seeds(seed)
    env = InventoryEnv(scenario)
    observation, _ = env.reset(seed=environment_seed)
    warmup = FixedOrderPolicy(20)
    for _ in range(shift_day):
        observation, _, _, _, _ = env.step(warmup.act(observation))

    memory = _make_memory(run_config)
    provider = CompatibleAPIProvider(
        ProviderConfig.from_env(profile, model_override=model_id)
    )
    agent = StructuredAgent(
        provider,
        memory,
        MovingAverageReorderPolicy(window=7, lead_time=scenario.supply.lead_time),
        top_k=2,
    )
    total_cost = 0.0
    invalid_reuse = 0
    for _ in range(post_shift_days):
        decision = agent.act(observation)
        if isinstance(memory, ShiftMemory):
            for memory_id in decision.used_memory_ids:
                if memory.get(memory_id).status not in {
                    MemoryStatus.ACTIVE,
                    MemoryStatus.PROBATION,
                }:
                    invalid_reuse += 1
        observation, _, _, _, record = env.step(decision.to_action())
        total_cost += float(record["total_cost"])
        agent.observe(record)
    return {
        "config_id": run_config["config_id"],
        "seed": seed,
        "cost": total_cost,
        "invalid_reuse": invalid_reuse,
        "tokens": sum(log.total_input_tokens + log.total_output_tokens for log in agent.logs),
        "fallbacks": sum(log.fallback_used for log in agent.logs),
        "calls": sum(log.attempt_count for log in agent.logs),
        "latency_ms": sum(log.total_latency_ms for log in agent.logs),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--rows-output", type=Path, required=True)
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    live = config["live_pilot"]
    run_configs = [{"config_id": "vector"}] + [
        {**candidate, "dormancy_patience": live["selected_dormancy_patience"]}
        for candidate in config["retrieval_grid"]
    ]
    existing: dict[tuple[str, int], dict[str, Any]] = {}
    if args.raw_output.exists():
        for line in args.raw_output.read_text(encoding="utf-8").splitlines():
            if line.strip():
                run = json.loads(line)
                existing[(run["config_id"], int(run["seed"]))] = run
    args.raw_output.parent.mkdir(parents=True, exist_ok=True)
    with args.raw_output.open("a", encoding="utf-8") as stream:
        for run_config in run_configs:
            for seed in live["seeds"]:
                key = (run_config["config_id"], int(seed))
                if key in existing:
                    continue
                run = run_one(
                    Path(live["scenario"]), int(seed), int(live["post_shift_days"]),
                    run_config, config["model"]["profile"], config["model"]["model_id"],
                )
                existing[key] = run
                stream.write(json.dumps(run, sort_keys=True) + "\n")
                stream.flush()
                print(json.dumps({"completed": key, "calls": run["calls"], "fallbacks": run["fallbacks"]}))
    rows = aggregate_rows(list(existing.values()))
    args.rows_output.parent.mkdir(parents=True, exist_ok=True)
    args.rows_output.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(rows), "estimated_calls": estimate_call_count({**live, "retrieval_grid": config["retrieval_grid"]})}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
