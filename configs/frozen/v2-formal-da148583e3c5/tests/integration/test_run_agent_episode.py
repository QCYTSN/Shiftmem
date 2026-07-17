import json
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "memory", ["none", "full_history", "summary", "vector", "time_decay"]
)
def test_cli_switches_all_memory_baselines(tmp_path: Path, memory: str) -> None:
    output = tmp_path / f"{memory}.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_agent_episode.py",
            "--config",
            "configs/environments/stable.yaml",
            "--memory",
            memory,
            "--seed",
            "42",
            "--max-days",
            "10",
            "--output",
            str(output),
        ],
        cwd=Path(__file__).parents[2],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    detail = json.loads(output.read_text(encoding="utf-8"))
    assert summary["memory"] == memory
    assert summary["days"] == 10
    assert summary["fallback_count"] == 0
    assert len(detail["decision_logs"]) == 10
