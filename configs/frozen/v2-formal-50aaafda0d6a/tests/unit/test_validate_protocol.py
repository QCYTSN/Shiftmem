from pathlib import Path

from scripts.validate_protocol import validate_protocol


COMPLETE_PROTOCOL = """# Experiment Protocol
## Status and amendment policy
Frozen before Test-ID and Test-OOD. Amendments are versioned and justified.
## Research questions and hypotheses
RQ1 RQ2 RQ3 RQ4 RQ5 H1 H2 H3 H4 H5
## Primary estimand and endpoint
ShiftMem versus VectorMemory; post_shift_cumulative_regret_30; lower is better.
## Secondary metrics
invalid memory reuse rate; total cost; recovery time; token; latency.
## Scenario splits and no-test-tuning
Development Validation Test-ID Test-OOD. Test-ID and Test-OOD are not used for tuning.
## Models and method matrix
core model A; core model B; supplementary model; six memory methods.
## Seeds, pairing, and failed runs
paired scenario model seed; failed provider runs retained; safe fallback.
## Statistical analysis
paired t-test; Wilcoxon signed-rank; Holm correction; alpha 0.05; effect size; 95% confidence interval.
## Exclusion and stopping rules
no silent deletion; parse failures included; predeclared diagnostic.
## Reproducibility and freeze
Git commit; dependency versions; model ID; configuration hash; SHA-256.
"""


def test_complete_protocol_has_no_validation_errors(tmp_path: Path) -> None:
    path = tmp_path / "protocol.md"
    path.write_text(COMPLETE_PROTOCOL, encoding="utf-8")
    assert validate_protocol(path) == []


def test_validator_reports_missing_sections_and_placeholders(tmp_path: Path) -> None:
    path = tmp_path / "protocol.md"
    path.write_text(
        "# Experiment Protocol\nThis document will record the protocol. TODO",
        encoding="utf-8",
    )

    errors = validate_protocol(path)

    assert any("placeholder" in error for error in errors)
    assert any("Primary estimand" in error for error in errors)
    assert any("no-test-tuning" in error for error in errors)


def test_validator_rejects_missing_protocol_file(tmp_path: Path) -> None:
    errors = validate_protocol(tmp_path / "missing.md")
    assert errors == ["protocol file does not exist"]
