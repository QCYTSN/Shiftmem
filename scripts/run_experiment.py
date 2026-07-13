"""Run a reproducible classical-policy experiment matrix."""

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from shiftmem.envs.inventory_env import InventoryEnv
from shiftmem.envs.shifts import load_scenario
from shiftmem.evaluation.metrics import summarize_episode
from run_episode import derive_seeds, make_policy


def load_experiment(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    required = {"name", "split", "seeds", "scenarios", "policies"}
    if set(config) != required:
        raise ValueError(f"experiment config must contain exactly {sorted(required)}")
    if not config["seeds"] or not config["scenarios"] or not config["policies"]:
        raise ValueError("experiment matrix dimensions must not be empty")
    return config


def run_matrix(config: dict[str, Any]) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for scenario_path in config["scenarios"]:
        scenario = load_scenario(scenario_path)
        shift_days = [shift.start_day for shift in scenario.shifts if shift.start_day > 0]
        shift_day = min(shift_days) if shift_days else None
        for seed in config["seeds"]:
            environment_seed, policy_seed = derive_seeds(int(seed))
            for policy_config in config["policies"]:
                policy_name = policy_config["name"]
                policy = make_policy(
                    policy_name,
                    int(policy_config.get("order_quantity", 20)),
                    policy_seed,
                    scenario.supply.lead_time,
                )
                env = InventoryEnv(scenario)
                observation, _ = env.reset(seed=environment_seed)
                terminated = False
                while not terminated:
                    action = (
                        policy.act(observation, env.oracle_context())
                        if policy_name == "oracle"
                        else policy.act(observation)
                    )
                    observation, _, terminated, _, _ = env.step(action)
                runs.append(
                    {
                        "experiment": config["name"],
                        "split": config["split"],
                        "scenario": scenario.name,
                        "policy": policy_name,
                        "seed": int(seed),
                        "shift_day": shift_day,
                        "metrics": summarize_episode(env.records, shift_day=shift_day),
                        "records": env.records,
                    }
                )
    return runs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = load_experiment(args.config)
    runs = run_matrix(config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        for run in runs:
            stream.write(json.dumps(run, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output), "runs": len(runs)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
