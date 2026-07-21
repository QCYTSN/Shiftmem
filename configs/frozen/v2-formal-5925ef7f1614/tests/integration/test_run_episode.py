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


def test_agent_cli_runs_shiftmem_and_writes_audit_summary(tmp_path: Path) -> None:
    output = tmp_path / "shiftmem.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_agent_episode.py",
            "--config",
            "configs/environments/stable.yaml",
            "--memory",
            "shiftmem",
            "--provider",
            "deterministic",
            "--max-days",
            "15",
            "--output",
            str(output),
        ],
        cwd=Path(__file__).parents[2],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    detail = json.loads(output.read_text(encoding="utf-8"))
    assert detail["summary"]["memory"] == "shiftmem"
    assert detail["summary"]["days"] == 15
    assert detail["memory_audit"]["experience_count"] >= 1
    serialized = json.dumps(detail["memory_audit"])
    assert "regime_id" not in serialized
    assert "oracle_context" not in serialized
