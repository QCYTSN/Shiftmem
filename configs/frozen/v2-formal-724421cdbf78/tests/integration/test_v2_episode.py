"""End-to-end offline test of the v2 hierarchical strategy episode."""

from pathlib import Path

from shiftmem.control.episode import V2EpisodeConfig, run_v2_episode
from shiftmem.envs.shifts import load_scenario
from shiftmem.memory.store import make_memory
from shiftmem.providers.local import DeterministicStrategyProvider

CONFIG = Path("configs/environments/demand_jump.yaml")


def _run(memory_name="vector", max_days=40, interval=5, cooldown=3):
    scenario = load_scenario(CONFIG)
    return run_v2_episode(
        scenario=scenario,
        provider=DeterministicStrategyProvider(),
        memory=make_memory(memory_name),
        config=V2EpisodeConfig(
            seed=42, max_days=max_days, review_interval=interval, cooldown=cooldown
        ),
    )


def test_every_day_has_a_controller_order():
    result = _run()
    records = result["environment_records"]
    assert len(records) == 40
    assert len(result["daily_decision_log"]) == 40
    # The deterministic controller must produce an order for every completed day.
    assert all("order_quantity" in record for record in records)
    assert all(
        set(row) == {"day", "active_strategy", "order"}
        for row in result["daily_decision_log"]
    )


def test_reviews_occur_only_on_scheduled_or_event_days():
    result = _run(max_days=40, interval=5)
    review_days = [log["day"] for log in result["review_logs"]]
    # Far fewer reviews than days: this is a low-frequency agent.
    assert len(review_days) < 40
    # Every periodic review day is a multiple of the interval.
    periodic = [d for log, d in zip(result["review_logs"], review_days)
                if log["trigger_reason"] == "periodic"]
    assert all(d % 5 == 0 for d in periodic)


def test_logs_separate_scheduler_memory_proposal_and_order():
    result = _run()
    assert "review_logs" in result
    assert "scheduler_log" in result
    assert "daily_decision_log" in result
    assert "environment_records" in result
    sample = result["review_logs"][0]
    for field in ("trigger_reason", "supplied_memory_ids", "cited_memory_ids",
                  "active_strategy", "proposal", "trigger_evidence"):
        assert field in sample

    for review in result["review_logs"]:
        if review["trigger_reason"] in {"event", "coalesced"}:
            assert review["trigger_evidence"]


def test_episode_is_deterministic():
    first = _run()
    second = _run()
    assert first["environment_records"] == second["environment_records"]


def test_vector_baseline_receives_delayed_strategy_experiences():
    result = _run(memory_name="vector", max_days=12, interval=5)
    reviews = result["review_logs"]
    assert reviews[0]["supplied_memory_ids"] == []
    assert reviews[1]["supplied_memory_ids"] == ["exp-v2ep-0"]


def test_shiftmem_runs_end_to_end_without_network():
    result = _run(memory_name="shiftmem", max_days=40)
    assert len(result["environment_records"]) == 40
    # ShiftMem records some auditable memory state by episode end.
    assert "memory_audit" in result
