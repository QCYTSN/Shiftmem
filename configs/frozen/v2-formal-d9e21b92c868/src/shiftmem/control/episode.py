"""End-to-end v2 episode loop: scheduler + agent + controller + memory.

Every day the deterministic controller places an order from the current
validated strategy. The scheduler gates low-frequency reviews; on a review day
the strategy agent proposes a bounded update, which is clamped and (for
lifecycle-aware memories) registered as a delayed-validated strategy revision.
This loop is network-free when given a deterministic provider.
"""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from shiftmem.agents.strategy_agent import StrategyReviewAgent
from shiftmem.envs.inventory_env import InventoryEnv
from shiftmem.envs.shifts import Scenario
from shiftmem.memory.reuse import classify_reuse
from shiftmem.memory.extractor import ExperienceExtractor
from shiftmem.memory.validator import DelayedValidator, PendingValidation, ValidationPolicy
from shiftmem.providers.base import ModelProvider

from .controller import DeterministicController, StrategyParameters
from .scheduler import ReviewScheduler


@dataclass
class V2EpisodeConfig:
    seed: int = 42
    max_days: int = 150
    review_interval: int = 5
    cooldown: int = 3
    top_k: int = 5
    episode_id: str = "v2ep"
    validation_service_window: int = 3


def run_v2_episode(
    scenario: Scenario,
    provider: ModelProvider,
    memory: Any,
    config: V2EpisodeConfig | None = None,
) -> dict[str, Any]:
    config = config or V2EpisodeConfig()
    env = InventoryEnv(scenario)
    controller = DeterministicController()
    scheduler = ReviewScheduler(interval=config.review_interval, cooldown=config.cooldown)
    agent = StrategyReviewAgent(provider=provider, memory=memory, top_k=config.top_k)

    strategy = StrategyParameters()
    scheduler_log: list[dict[str, Any]] = []
    daily_decision_log: list[dict[str, Any]] = []
    pending_event: dict[str, Any] | None = None
    baseline_experiences = _BaselineStrategyExperiences(
        memory, config.validation_service_window
    )

    observation, _ = env.reset(seed=config.seed)
    terminated = False
    register_revision = getattr(memory, "register_strategy_revision", None)
    observe_outcome = getattr(memory, "observe_outcome", None)

    while not terminated and len(env.records) < config.max_days:
        day = int(observation["day"])
        event = pending_event is not None
        decision = scheduler.evaluate(day, event=event, evidence=pending_event)
        scheduler_log.append(
            {
                "day": day,
                "trigger": decision.trigger,
                "should_review": decision.should_review,
                "coalesced": decision.coalesced,
                "cooldown_suppressed": decision.cooldown_suppressed,
            }
        )
        pending_event = None

        if decision.should_review:
            trigger_reason = decision.trigger
            set_decision = getattr(provider, "set_decision", None)
            if callable(set_decision):
                set_decision(config.episode_id, day)
            new_strategy = agent.review(
                observation,
                strategy,
                trigger_reason,
                decision.evidence or {},
            )
            review_log = agent.logs[-1]
            if callable(register_revision) and not review_log.fallback_used:
                revision = {
                    "trigger": trigger_reason,
                    "previous": strategy.model_dump(),
                    "proposed": new_strategy.model_dump(),
                }
                register_revision(
                    config.episode_id,
                    day,
                    observation,
                    revision,
                    list(review_log.cited_memory_ids),
                )
            elif not review_log.fallback_used:
                baseline_experiences.register(
                    config.episode_id,
                    day,
                    observation,
                    {
                        "trigger": trigger_reason,
                        "previous": strategy.model_dump(),
                        "proposed": new_strategy.model_dump(),
                    },
                )
            strategy = new_strategy

        action = controller.order(observation, strategy)
        daily_decision_log.append(
            {
                "day": day,
                "active_strategy": strategy.model_dump(),
                "order": dict(action),
            }
        )
        observation, _, terminated, _, record = env.step(action)

        if callable(observe_outcome):
            signals = observe_outcome(record)
            # A change signal on this outcome requests an extra review next day.
            if _raised_change(memory):
                pending_event = {"variable": "outcome", "day": int(record["day"])}
        else:
            baseline_experiences.observe(record)

    review_logs = [log.model_dump(mode="json") for log in agent.logs]
    reuse = [
        classify_reuse(
            supplied_ids=log.supplied_memory_ids,
            cited_ids=log.cited_memory_ids,
            proposal_accepted=not log.fallback_used,
        )
        for log in agent.logs
    ]
    result: dict[str, Any] = {
        "environment_records": env.records,
        "review_logs": review_logs,
        "scheduler_log": scheduler_log,
        "daily_decision_log": daily_decision_log,
        "reuse_attribution": [
            {
                "reused": r.reused,
                "retrieved_not_cited": r.retrieved_not_cited,
                "cited_but_rejected": r.cited_but_rejected,
            }
            for r in reuse
        ],
        "fallback_count": sum(log.fallback_used for log in agent.logs),
        "review_count": len(agent.logs),
    }
    audit_summary = getattr(memory, "audit_summary", None)
    if callable(audit_summary):
        result["memory_audit"] = audit_summary()
    return result


class _BaselineStrategyExperiences:
    """Give non-lifecycle baselines the same delayed strategy experience unit."""

    def __init__(self, memory: Any, service_window: int) -> None:
        self.memory = memory
        self.validator = DelayedValidator(
            ValidationPolicy(service_window=service_window)
        )
        self.extractor = ExperienceExtractor()
        self.history: list[dict[str, Any]] = []
        self.pending: dict[str, tuple[PendingValidation, dict[str, Any]]] = {}

    def register(
        self,
        episode_id: str,
        step: int,
        observation: dict[str, Any],
        revision: dict[str, Any],
    ) -> None:
        memory_id = f"exp-{episode_id}-{step}"
        pending = self.validator.register(
            memory_id,
            decision_step=step,
            quoted_lead_time=int(observation["quoted_lead_time"]),
        )
        self.pending[memory_id] = (
            pending,
            {
                "episode_id": episode_id,
                "step": step,
                "observation": deepcopy(observation),
                "revision": deepcopy(revision),
            },
        )

    def observe(self, record: dict[str, Any]) -> None:
        self.history.append(deepcopy(record))
        current_step = int(record["day"]) + 1
        for memory_id, (pending, source) in list(self.pending.items()):
            if current_step < pending.due_step:
                continue
            result = self.validator.evaluate(
                pending, self.history, current_step=current_step
            )
            experience = self.extractor.extract_strategy_revision(
                source["episode_id"],
                source["step"],
                source["observation"],
                source["revision"],
                result,
            )
            self.memory.add(experience.to_memory_record())
            del self.pending[memory_id]


def _raised_change(memory: Any) -> bool:
    """Detect whether the memory flagged a change on the latest outcome."""

    changed = getattr(memory, "_changed_at", None)
    if not isinstance(changed, dict) or not changed:
        return False
    # Report an event only once per newly recorded change step.
    seen = getattr(memory, "_v2_seen_changes", None)
    if seen is None:
        seen = set()
        setattr(memory, "_v2_seen_changes", seen)
    latest = max(changed.values())
    if latest in seen:
        return False
    seen.add(latest)
    return True
