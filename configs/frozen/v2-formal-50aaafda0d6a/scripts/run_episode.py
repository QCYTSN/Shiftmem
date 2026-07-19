"""Run one reproducible inventory episode without an LLM."""

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from shiftmem.agents.classical import (
    ExponentialSmoothingPolicy,
    FixedOrderPolicy,
    MovingAverageReorderPolicy,
    OraclePolicy,
    RandomOrderPolicy,
)
from shiftmem.envs.inventory_env import InventoryEnv
from shiftmem.envs.shifts import load_scenario
from shiftmem.evaluation.metrics import summarize_episode
from shiftmem.evaluation.plots import plot_episode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--policy",
        choices=("fixed", "random", "moving_average", "exponential", "oracle"),
        default="fixed",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--order-quantity", type=int, default=20)
    parser.add_argument("--figure", type=Path)
    return parser


def make_policy(name: str, order_quantity: int, seed: int, lead_time: int) -> Any:
    if name == "fixed":
        return FixedOrderPolicy(order_quantity)
    if name == "random":
        return RandomOrderPolicy(0, max(1, order_quantity * 2), seed)
    if name == "moving_average":
        return MovingAverageReorderPolicy(window=7, lead_time=lead_time)
    if name == "exponential":
        return ExponentialSmoothingPolicy(alpha=0.3, lead_time=lead_time)
    return OraclePolicy()


def derive_seeds(seed: int) -> tuple[int, int]:
    """Derive independent reproducible environment and policy seeds."""
    environment_sequence, policy_sequence = np.random.SeedSequence(seed).spawn(2)
    environment_seed = int(environment_sequence.generate_state(1)[0])
    policy_seed = int(policy_sequence.generate_state(1)[0])
    return environment_seed, policy_seed


def main() -> int:
    args = build_parser().parse_args()
    scenario = load_scenario(args.config)
    env = InventoryEnv(scenario)
    environment_seed, policy_seed = derive_seeds(args.seed)
    policy = make_policy(
        args.policy, args.order_quantity, policy_seed, scenario.supply.lead_time
    )
    observation, _ = env.reset(seed=environment_seed)
    terminated = False
    while not terminated:
        if args.policy == "oracle":
            action = policy.act(observation, env.oracle_context())
        else:
            action = policy.act(observation)
        observation, _, terminated, _, _ = env.step(action)
    summary = summarize_episode(env.records)
    if args.figure:
        plot_episode(
            env.records,
            args.figure,
            shift_days=[shift.start_day for shift in scenario.shifts],
        )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
