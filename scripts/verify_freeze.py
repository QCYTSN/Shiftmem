"""Verify hashes and file membership of a frozen experiment package.

Text files accept only CRLF/LF transport normalization as byte-equivalent.
This keeps manifests portable across GitHub Desktop and CLI checkouts while
still rejecting every semantic content change and every binary-byte change.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def _matches_hash(path: Path, expected: str) -> bool:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() == expected:
        return True
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return False
    canonical = text.replace("\r\n", "\n").replace("\r", "\n")
    variants = (
        canonical.encode("utf-8"),
        canonical.replace("\n", "\r\n").encode("utf-8"),
    )
    return any(hashlib.sha256(value).hexdigest() == expected for value in variants)


def verify_freeze(freeze: Path) -> list[str]:
    manifest = freeze / "manifest.sha256"
    if not manifest.is_file():
        return ["manifest.sha256 is missing"]
    errors: list[str] = []
    declared: set[Path] = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        try:
            expected, name = line.split("  ", 1)
        except ValueError:
            errors.append(f"malformed manifest line: {line}")
            continue
        relative = Path(name)
        declared.add(relative)
        target = freeze / relative
        if not target.is_file():
            errors.append(f"missing file: {name}")
        elif not _matches_hash(target, expected):
            errors.append(f"hash mismatch: {name}")
    actual = {
        path.relative_to(freeze)
        for path in freeze.rglob("*")
        if path.is_file() and path != manifest
    }
    for extra in sorted(actual - declared):
        errors.append(f"undeclared file: {extra.as_posix()}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("freeze", type=Path)
    args = parser.parse_args()
    errors = verify_freeze(args.freeze)
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"verified {args.freeze}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
