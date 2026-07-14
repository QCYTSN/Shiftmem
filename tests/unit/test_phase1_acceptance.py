import copy

from scripts.run_phase1_acceptance import execute_acceptance


def make_config() -> dict:
    return {
        "name": "phase1_acceptance",
        "split": "development",
        "seeds": list(range(100)),
        "scenarios": [f"scenario-{index}" for index in range(5)],
        "policies": [{"name": name} for name in ("fixed", "random", "moving_average", "exponential", "oracle")],
        "expected_horizon": 150,
    }


def make_runs(config: dict) -> list[dict]:
    runs = []
    for scenario_index, scenario in enumerate(config["scenarios"]):
        shift_day = None if scenario_index == 0 else 75
        for seed in config["seeds"]:
            demand = [20 + ((seed + day) % 3) for day in range(150)]
            for policy in config["policies"]:
                name = policy["name"]
                cost = 100.0 if name == "oracle" else 200.0 if name == "random" else 150.0
                runs.append(
                    {
                        "scenario": scenario,
                        "policy": name,
                        "seed": seed,
                        "shift_day": shift_day,
                        "metrics": {"days": 150, "total_cost": cost},
                        "records": [{"day": day, "demand": value} for day, value in enumerate(demand)],
                    }
                )
    return runs


def test_acceptance_passes_exact_2500_run_matrix() -> None:
    config = make_config()
    summary = execute_acceptance(config, lambda _: make_runs(config))
    assert summary.passed
    assert summary.expected_runs == summary.completed_runs == 2500
    assert all(summary.gates.values())


def test_acceptance_rejects_missing_run() -> None:
    config = make_config()
    runs = make_runs(config)[:-1]
    summary = execute_acceptance(config, lambda _: runs)
    assert not summary.gates["complete_matrix"]


def test_acceptance_rejects_nonfinite_metric_and_wrong_horizon() -> None:
    config = make_config()
    runs = make_runs(config)
    runs[0]["metrics"]["total_cost"] = float("nan")
    runs[1]["metrics"]["days"] = 149
    summary = execute_acceptance(config, lambda _: runs)
    assert not summary.gates["finite_metrics"]
    assert not summary.gates["expected_horizon"]


def test_acceptance_rejects_unpaired_demand() -> None:
    config = make_config()
    runs = make_runs(config)
    runs[1]["records"][0]["demand"] += 1
    summary = execute_acceptance(config, lambda _: runs)
    assert not summary.gates["paired_demand"]


def test_acceptance_requires_oracle_to_beat_random_in_every_scenario() -> None:
    config = make_config()
    runs = make_runs(config)
    for run in runs:
        if run["scenario"] == "scenario-3" and run["policy"] == "oracle":
            run["metrics"]["total_cost"] = 300.0
    summary = execute_acceptance(config, lambda _: runs)
    assert not summary.gates["oracle_beats_random"]


def test_acceptance_rejects_inconsistent_shift_markers() -> None:
    config = make_config()
    runs = make_runs(config)
    broken = copy.deepcopy(runs)
    broken[501]["shift_day"] = 80
    summary = execute_acceptance(config, lambda _: broken)
    assert not summary.gates["valid_shift_markers"]
