"""Verify the tracked Protocol-v2 raw-evidence release archive."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence
from zipfile import BadZipFile, ZipFile


DEFAULT_MANIFEST = Path("artifacts/aggregated/v2_formal_evidence_manifest.json")


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_release_archive(
    root: str | Path,
    manifest_path: str | Path = DEFAULT_MANIFEST,
) -> dict[str, Any]:
    """Verify archive identity and every manifest-declared raw source."""

    repository = Path(root).resolve()
    manifest_file = repository / Path(manifest_path)
    manifest: Mapping[str, Any] = json.loads(
        manifest_file.read_text(encoding="utf-8")
    )
    evidence_id = str(manifest["evidence_freeze_id"])
    release_dir = repository / "artifacts" / "releases"
    archive_path = release_dir / f"{evidence_id}-raw-evidence.zip"
    checksum_path = release_dir / f"{evidence_id}-raw-evidence.sha256.json"
    checksum: Mapping[str, Any] = json.loads(
        checksum_path.read_text(encoding="utf-8")
    )

    errors: list[str] = []
    if checksum.get("evidence_freeze_id") != evidence_id:
        errors.append("checksum evidence identity does not match the manifest")
    if checksum.get("archive") != archive_path.name:
        errors.append("checksum archive name does not match the release file")
    if int(checksum.get("archive_bytes", -1)) != archive_path.stat().st_size:
        errors.append("archive byte count does not match the checksum record")
    if str(checksum.get("archive_sha256", "")) != _file_sha256(archive_path):
        errors.append("archive SHA-256 does not match the checksum record")

    sources = tuple(
        source
        for source in manifest.get("files", ())
        if Path(str(source.get("path", ""))).as_posix().startswith(
            "artifacts/raw_runs/"
        )
    )
    try:
        with ZipFile(archive_path) as archive:
            members = archive.namelist()
            duplicate_names = sorted(
                {name for name in members if members.count(name) > 1}
            )
            if duplicate_names:
                errors.append(
                    "archive contains duplicate members: " + ", ".join(duplicate_names)
                )
            member_set = set(members)
            for source in sources:
                relative = str(source["path"])
                member = Path(relative).name
                if member not in member_set:
                    errors.append(f"archive is missing {relative}")
                    continue
                content = archive.read(member)
                if len(content) != int(source.get("bytes", -1)):
                    errors.append(f"byte count mismatch for {relative}")
                if sha256(content).hexdigest() != str(source.get("sha256", "")):
                    errors.append(f"SHA-256 mismatch for {relative}")
                if source.get("records") is not None:
                    records = sum(1 for line in content.splitlines() if line.strip())
                    if records != int(source["records"]):
                        errors.append(f"record count mismatch for {relative}")
            expected_members = {Path(str(source["path"])).name for source in sources}
            unexpected = sorted(member_set - expected_members)
            if unexpected:
                errors.append(
                    "archive contains undeclared members: " + ", ".join(unexpected)
                )
    except BadZipFile:
        errors.append("release archive is not a valid ZIP file")

    if int(checksum.get("raw_files", -1)) != len(sources):
        errors.append("checksum raw-file count does not match the manifest")

    return {
        "valid": not errors,
        "evidence_freeze_id": evidence_id,
        "archive": archive_path.relative_to(repository).as_posix(),
        "declared_files": len(sources),
        "errors": errors,
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    result = verify_release_archive(args.root, args.manifest)
    print(json.dumps(result, indent=2))
    return int(not result["valid"])


if __name__ == "__main__":
    raise SystemExit(main())
