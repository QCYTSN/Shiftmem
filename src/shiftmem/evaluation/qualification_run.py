"""Immutable metadata and output guards for model-qualification runs."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import subprocess
from typing import Iterable

from pydantic import BaseModel, ConfigDict


class QualificationRunMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    started_at_utc: str
    schema_name: str
    config_sha256: str
    system_prompt_sha256: str
    user_message_builder: str
    git_revision: str | None
    git_dirty: bool | None


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git_value(args: list[str], cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def build_run_metadata(
    *,
    run_id: str,
    schema: str,
    config_bytes: bytes,
    system_prompt: str,
    builder_name: str,
    cwd: Path | None = None,
) -> QualificationRunMetadata:
    workdir = cwd or Path.cwd()
    revision = _git_value(["rev-parse", "HEAD"], workdir)
    status = _git_value(["status", "--porcelain"], workdir)
    return QualificationRunMetadata(
        run_id=run_id,
        started_at_utc=datetime.now(timezone.utc).isoformat(),
        schema_name=schema,
        config_sha256=sha256_bytes(config_bytes),
        system_prompt_sha256=sha256_bytes(system_prompt.encode("utf-8")),
        user_message_builder=builder_name,
        git_revision=revision,
        git_dirty=None if status is None else bool(status),
    )


def ensure_output_paths_available(
    paths: Iterable[Path], *, overwrite: bool = False
) -> None:
    existing = [path for path in paths if path.exists()]
    if existing and not overwrite:
        joined = ", ".join(str(path) for path in existing)
        raise FileExistsError(f"qualification outputs already exist: {joined}")
