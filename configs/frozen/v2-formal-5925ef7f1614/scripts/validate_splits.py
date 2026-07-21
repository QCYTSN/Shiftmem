"""Validate all four research split manifests without running outcomes."""

import argparse
import json
from pathlib import Path

from shiftmem.evaluation.splits import validate_split_manifests


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifests", type=Path, nargs="+")
    args = parser.parse_args()
    errors = validate_split_manifests(args.manifests, require_all=True)
    print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
