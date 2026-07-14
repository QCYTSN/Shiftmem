"""Validate that the ShiftMem experiment protocol is complete and freeze-ready."""

import argparse
from pathlib import Path


REQUIRED_SECTIONS = (
    "Status and amendment policy",
    "Research questions and hypotheses",
    "Primary estimand and endpoint",
    "Secondary metrics",
    "Scenario splits and no-test-tuning",
    "Models and method matrix",
    "Seeds, pairing, and failed runs",
    "Statistical analysis",
    "Exclusion and stopping rules",
    "Reproducibility and freeze",
)

REQUIRED_TERMS = (
    "RQ1",
    "RQ2",
    "RQ3",
    "RQ4",
    "RQ5",
    "H1",
    "H2",
    "H3",
    "H4",
    "H5",
    "ShiftMem versus VectorMemory",
    "post_shift_cumulative_regret_30",
    "Development",
    "Validation",
    "Test-ID",
    "Test-OOD",
    "paired t-test",
    "Wilcoxon signed-rank",
    "Holm correction",
    "alpha 0.05",
    "SHA-256",
)

PLACEHOLDERS = ("TBD", "TODO", "FIXME", "will record")


def validate_protocol(path: Path) -> list[str]:
    if not path.is_file():
        return ["protocol file does not exist"]
    text = path.read_text(encoding="utf-8")
    lower = text.lower()
    errors: list[str] = []
    for placeholder in PLACEHOLDERS:
        if placeholder.lower() in lower:
            errors.append(f"placeholder text is forbidden: {placeholder}")
    for section in REQUIRED_SECTIONS:
        if f"## {section}".lower() not in lower:
            errors.append(f"missing required section: {section}")
    for term in REQUIRED_TERMS:
        if term.lower() not in lower:
            errors.append(f"missing required term: {term}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    errors = validate_protocol(args.path)
    for error in errors:
        print(error)
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
