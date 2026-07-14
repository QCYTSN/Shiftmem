"""Canonical split manifests and leakage checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


SplitName = Literal["Development", "Validation", "Test-ID", "Test-OOD"]


class ScenarioEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    path: Path
    held_out_dimensions: list[str] = Field(default_factory=list)


class SplitManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    split: SplitName
    selection_access: Literal["allowed", "config_only"]
    seeds: list[int] = Field(min_length=1)
    scenarios: list[ScenarioEntry] = Field(min_length=1)


def hash_scenario(path: str | Path) -> str:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    canonical = json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_split_manifest(path: str | Path) -> SplitManifest:
    manifest_path = Path(path).resolve()
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    for entry in data.get("scenarios", []):
        scenario_path = Path(entry["path"])
        if not scenario_path.is_absolute():
            scenario_path = manifest_path.parent / scenario_path
        entry["path"] = scenario_path.resolve()
    return SplitManifest.model_validate(data)


def validate_split_manifests(
    paths: list[str | Path], *, require_all: bool = False
) -> list[str]:
    errors: list[str] = []
    manifests: list[SplitManifest] = []
    for path in paths:
        try:
            manifests.append(load_split_manifest(path))
        except Exception as error:
            errors.append(f"invalid manifest {path}: {error}")
    if require_all:
        present = {manifest.split for manifest in manifests}
        for missing in sorted(
            {"Development", "Validation", "Test-ID", "Test-OOD"} - present
        ):
            errors.append(f"missing split manifest: {missing}")

    ids: dict[str, str] = {}
    hashes: dict[str, str] = {}
    seed_owner: dict[int, str] = {}
    for manifest in manifests:
        if len(manifest.seeds) != len(set(manifest.seeds)):
            errors.append(f"duplicate seed within {manifest.split}")
        if manifest.split in {"Test-ID", "Test-OOD"}:
            if manifest.selection_access != "config_only":
                errors.append(f"{manifest.split} selection_access must be config_only")
        elif manifest.selection_access != "allowed":
            errors.append(f"{manifest.split} selection_access must be allowed")
        for seed in manifest.seeds:
            if seed < 0:
                errors.append(f"negative seed in {manifest.split}: {seed}")
            owner = seed_owner.setdefault(seed, manifest.split)
            if owner != manifest.split:
                errors.append(
                    f"seed overlap between {owner} and {manifest.split}: {seed}"
                )
        for entry in manifest.scenarios:
            if entry.id in ids:
                errors.append(
                    f"duplicate scenario id across {ids[entry.id]} and {manifest.split}: {entry.id}"
                )
            else:
                ids[entry.id] = manifest.split
            if not entry.path.is_file():
                errors.append(f"scenario does not exist: {entry.path}")
                continue
            try:
                digest = hash_scenario(entry.path)
            except Exception as error:
                errors.append(f"invalid scenario {entry.path}: {error}")
                continue
            if digest in hashes:
                errors.append(
                    f"duplicate scenario hash across {hashes[digest]} and {manifest.split}: {digest}"
                )
            else:
                hashes[digest] = manifest.split
            if manifest.split == "Test-OOD" and not entry.held_out_dimensions:
                errors.append(f"Test-OOD scenario {entry.id} requires held-out dimensions")
    return errors
