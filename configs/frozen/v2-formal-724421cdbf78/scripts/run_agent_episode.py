"""Run an offline structured agent with a selectable memory baseline."""

import argparse
import json
from pathlib import Path

from shiftmem.agents.classical import FixedOrderPolicy
from shiftmem.agents.llm_agent import StructuredAgent
from shiftmem.control.episode import V2EpisodeConfig, run_v2_episode
from shiftmem.envs.inventory_env import InventoryEnv
from shiftmem.envs.shifts import load_scenario
from shiftmem.evaluation.metrics import summarize_episode
from shiftmem.memory.store import make_memory
from shiftmem.providers.local import DeterministicProvider, DeterministicStrategyProvider
from shiftmem.providers.compatible_api import CompatibleAPIProvider, ProviderConfig


def make_provider(
    name: str,
    target_inventory: int,
    model_name: str | None = None,
    strategy: bool = False,
):
    if name == "deterministic":
        return DeterministicStrategyProvider() if strategy else DeterministicProvider(target_inventory)
    if name in {"compatible", "bailian", "siliconflow"}:
        return CompatibleAPIProvider(
            ProviderConfig.from_env(name, model_override=model_name)
        )
    raise ValueError(f"unknown provider: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--memory",
        choices=("none", "full_history", "summary", "vector", "time_decay", "shiftmem"),
        required=True,
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-days", type=int, default=150)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--target-inventory", type=int, default=60)
    parser.add_argument(
        "--provider",
        choices=("deterministic", "compatible", "bailian", "siliconflow"),
        default="deterministic",
    )
    parser.add_argument("--model-name")
    parser.add_argument(
        "--protocol",
        choices=("v1", "v2"),
        default="v1",
        help="v1 = direct daily order (archived); v2 = low-frequency strategy review",
    )
    parser.add_argument("--review-interval", type=int, default=5)
    parser.add_argument("--cooldown", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.max_days < 1:
        parser.error("--max-days must be positive")

    scenario = load_scenario(args.config)

    if args.protocol == "v2":
        provider = make_provider(
            args.provider, args.target_inventory, args.model_name, strategy=True
        )
        result = run_v2_episode(
            scenario=scenario,
            provider=provider,
            memory=make_memory(args.memory),
            config=V2EpisodeConfig(
                seed=args.seed,
                max_days=args.max_days,
                review_interval=args.review_interval,
                cooldown=args.cooldown,
            ),
        )
        metrics = summarize_episode(result["environment_records"])
        summary = {
            "protocol": "v2",
            "memory": args.memory,
            **metrics,
            "review_count": result["review_count"],
            "fallback_count": result["fallback_count"],
        }
        detail = {"summary": summary, **result}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(detail, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0

    env = InventoryEnv(scenario)
    agent = StructuredAgent(
        provider=make_provider(args.provider, args.target_inventory, args.model_name),
        memory=make_memory(args.memory),
        fallback=FixedOrderPolicy(20),
        top_k=args.top_k,
    )
    observation, _ = env.reset(seed=args.seed)
    terminated = False
    while not terminated and len(env.records) < args.max_days:
        decision = agent.act(observation)
        observation, _, terminated, _, record = env.step(decision.to_action())
        agent.observe(record)

    metrics = summarize_episode(env.records)
    summary = {
        "memory": args.memory,
        **metrics,
        "fallback_count": sum(log.fallback_used for log in agent.logs),
        "parse_failure_count": sum(log.parse_failure_count for log in agent.logs),
        "input_tokens": sum(log.total_input_tokens for log in agent.logs),
        "output_tokens": sum(log.total_output_tokens for log in agent.logs),
        "latency_ms": sum(log.total_latency_ms for log in agent.logs),
    }
    detail = {
        "summary": summary,
        "decision_logs": [log.model_dump(mode="json") for log in agent.logs],
        "environment_records": env.records,
    }
    audit_summary = getattr(agent.memory, "audit_summary", None)
    if callable(audit_summary):
        detail["memory_audit"] = audit_summary()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(detail, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
