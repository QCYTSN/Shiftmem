from pathlib import Path

import yaml

from shiftmem.evaluation.splits import (
    hash_scenario,
    load_split_manifest,
    validate_split_manifests,
)


def write_scenario(path: Path, name: str, base: int = 20) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "name": name,
                "episode_length": 20,
                "initial_inventory": 20,
                "demand_model": "poisson",
                "demand": {"base_level": base, "dispersion": 10},
                "supply": {"lead_time": 1, "fill_rate": 1.0},
                "costs": {"purchase": 1, "holding": 0.1, "stockout": 5, "fixed_order": 0},
                "shifts": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def write_manifest(path: Path, split: str, seed: int, scenario: Path, **entry) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "split": split,
                "selection_access": "allowed" if split in {"Development", "Validation"} else "config_only",
                "seeds": [seed],
                "scenarios": [{"id": f"{split.lower()}-one", "path": str(scenario), **entry}],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_hash_is_semantic_and_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.yaml"
    second = tmp_path / "second.yaml"
    write_scenario(first, "same")
    data = yaml.safe_load(first.read_text(encoding="utf-8"))
    second.write_text(yaml.safe_dump(data, sort_keys=True), encoding="utf-8")
    assert hash_scenario(first) == hash_scenario(first)
    assert hash_scenario(first) == hash_scenario(second)


def test_load_resolves_scenario_paths_relative_to_manifest(tmp_path: Path) -> None:
    scenario = tmp_path / "scenario.yaml"
    manifest = tmp_path / "manifest.yaml"
    write_scenario(scenario, "one")
    write_manifest(manifest, "Development", 1, Path("scenario.yaml"))
    loaded = load_split_manifest(manifest)
    assert loaded.scenarios[0].path == scenario.resolve()


def test_validation_rejects_duplicate_ids_hashes_and_seed_overlap(tmp_path: Path) -> None:
    one = tmp_path / "one.yaml"
    clone = tmp_path / "clone.yaml"
    write_scenario(one, "same")
    clone.write_text(one.read_text(encoding="utf-8"), encoding="utf-8")
    development = tmp_path / "development.yaml"
    validation = tmp_path / "validation.yaml"
    write_manifest(development, "Development", 7, one)
    write_manifest(validation, "Validation", 7, clone)
    data = yaml.safe_load(validation.read_text(encoding="utf-8"))
    data["scenarios"][0]["id"] = "development-one"
    validation.write_text(yaml.safe_dump(data), encoding="utf-8")
    errors = validate_split_manifests([development, validation])
    assert any("duplicate scenario id" in error for error in errors)
    assert any("duplicate scenario hash" in error for error in errors)
    assert any("seed overlap" in error for error in errors)


def test_test_ood_requires_held_out_dimensions(tmp_path: Path) -> None:
    scenario = tmp_path / "ood.yaml"
    manifest = tmp_path / "ood-manifest.yaml"
    write_scenario(scenario, "ood")
    write_manifest(manifest, "Test-OOD", 30, scenario)
    assert any(
        "held-out" in error for error in validate_split_manifests([manifest])
    )


def test_test_splits_must_be_config_only(tmp_path: Path) -> None:
    scenario = tmp_path / "test.yaml"
    manifest = tmp_path / "test-manifest.yaml"
    write_scenario(scenario, "test")
    write_manifest(manifest, "Test-ID", 20, scenario)
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    data["selection_access"] = "allowed"
    manifest.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert any("config_only" in error for error in validate_split_manifests([manifest]))


def test_duplicate_id_and_hash_within_one_manifest_are_rejected(tmp_path: Path) -> None:
    scenario = tmp_path / "same.yaml"
    manifest = tmp_path / "development.yaml"
    write_scenario(scenario, "same")
    write_manifest(manifest, "Development", 1, scenario)
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    data["scenarios"].append(dict(data["scenarios"][0]))
    manifest.write_text(yaml.safe_dump(data), encoding="utf-8")
    errors = validate_split_manifests([manifest])
    assert any("duplicate scenario id" in error for error in errors)
    assert any("duplicate scenario hash" in error for error in errors)
