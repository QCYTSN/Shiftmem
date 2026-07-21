import json
from pathlib import Path
import subprocess
import sys

import yaml


def test_experiment_cli_runs_matrix_with_paired_demand(tmp_path: Path) -> None:
    config = tmp_path / "experiment.yaml"
    output = tmp_path / "runs.jsonl"
    config.write_text(
        yaml.safe_dump(
            {
                "name": "integration",
                "split": "development",
                "seeds": [3, 4],
                "scenarios": ["configs/environments/stable.yaml"],
                "policies": [
                    {"name": "fixed", "order_quantity": 20},
                    {"name": "moving_average", "order_quantity": 20},
                ],
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "scripts/run_experiment.py", "--config", str(config), "--output", str(output)],
        cwd=Path(__file__).parents[2],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    runs = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(runs) == 4
    for seed in (3, 4):
        paired = [run for run in runs if run["seed"] == seed]
        assert len(paired) == 2
        assert [r["demand"] for r in paired[0]["records"]] == [
            r["demand"] for r in paired[1]["records"]
        ]
