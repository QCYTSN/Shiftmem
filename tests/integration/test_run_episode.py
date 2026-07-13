import json
from pathlib import Path
import subprocess
import sys


def test_cli_runs_150_day_episode_and_writes_figure(tmp_path: Path) -> None:
    figure = tmp_path / "episode.png"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_episode.py",
            "--config",
            "configs/environments/stable.yaml",
            "--policy",
            "fixed",
            "--order-quantity",
            "20",
            "--seed",
            "42",
            "--figure",
            str(figure),
        ],
        cwd=Path(__file__).parents[2],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["days"] == 150
    assert summary["total_cost"] >= 0
    assert 0 <= summary["service_level"] <= 1
    assert figure.exists()
    assert figure.stat().st_size > 0
