"""Manifest-driven data access for the offline ShiftMem demonstration.

The Demo never discovers formal cells by globbing ``artifacts/raw_runs``.
Continuations and historical freezes intentionally coexist there, so only the
cell files declared by the final evidence manifest are eligible for display.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping
from zipfile import BadZipFile, ZipFile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "artifacts/aggregated/v2_formal_evidence_manifest.json"
DEFAULT_STATISTICS = ROOT / "artifacts/aggregated/v2_formal_statistical_analysis.json"

METHOD_LABELS = {
    "shiftmem": "ShiftMem",
    "vector": "Vector memory",
}

EVENT_ORDER = {
    "regime": 0,
    "review_event": 1,
    "review_periodic": 2,
    "fallback": 3,
    "memory": 4,
    "stockout": 5,
}


@dataclass(frozen=True, order=True)
class PairKey:
    """Identity shared by a paired ShiftMem-versus-Vector comparison."""

    split: str
    scenario_id: str
    model: str
    seed: int

    @property
    def label(self) -> str:
        return f"{self.scenario_id} · {self.model} · seed {self.seed}"


@dataclass(frozen=True)
class EvidenceCell:
    """One complete formal cell plus its declared source."""

    payload: Mapping[str, Any]
    source: str
    split: str

    @property
    def cell_id(self) -> str:
        return str(self.payload["cell_id"])

    @property
    def pair_key(self) -> PairKey:
        return PairKey(
            split=self.split,
            scenario_id=str(self.payload["scenario_id"]),
            model=str(self.payload["model"]),
            seed=int(self.payload["seed"]),
        )

    @property
    def method(self) -> str:
        return str(self.payload["method"])

    @property
    def method_label(self) -> str:
        return METHOD_LABELS.get(self.method, self.method)

    @property
    def shift_day(self) -> int | None:
        value = self.payload.get("shift_day")
        return None if value is None else int(value)

    @property
    def days(self) -> int:
        return len(self.payload.get("environment_records", []))

    @property
    def endpoint_applicable(self) -> bool:
        return bool(self.payload.get("endpoint_applicable", False))


@dataclass(frozen=True)
class EvidenceEvent:
    """Auditable event shown on the shared episode timeline."""

    day: int
    kind: str
    label: str
    detail: str

    @property
    def sort_key(self) -> tuple[int, int, str]:
        return (self.day, EVENT_ORDER.get(self.kind, 99), self.label)


@dataclass(frozen=True)
class VerificationResult:
    checked: int
    valid: bool
    errors: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceBundle:
    """Validated, indexed collection of formal cells."""

    root: Path
    manifest: Mapping[str, Any]
    cells: tuple[EvidenceCell, ...]
    cells_by_id: Mapping[str, EvidenceCell]
    pairs: Mapping[PairKey, Mapping[str, EvidenceCell]]
    verification: VerificationResult

    @property
    def evidence_id(self) -> str:
        return str(self.manifest["evidence_freeze_id"])

    @property
    def primary_pair_count(self) -> int:
        return sum(
            1
            for pair in self.pairs.values()
            if len(pair) == 2 and all(cell.endpoint_applicable for cell in pair.values())
        )

    @property
    def complete_pair_count(self) -> int:
        return sum(1 for pair in self.pairs.values() if len(pair) == 2)

    def available_splits(self) -> tuple[str, ...]:
        return tuple(sorted({key.split for key in self.pairs}, key=_split_sort_key))

    def scenarios(self, split: str) -> tuple[str, ...]:
        return tuple(sorted({key.scenario_id for key in self.pairs if key.split == split}))

    def models(self, split: str, scenario_id: str) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    key.model
                    for key in self.pairs
                    if key.split == split and key.scenario_id == scenario_id
                }
            )
        )

    def seeds(self, split: str, scenario_id: str, model: str) -> tuple[int, ...]:
        return tuple(
            sorted(
                {
                    key.seed
                    for key in self.pairs
                    if key.split == split
                    and key.scenario_id == scenario_id
                    and key.model == model
                }
            )
        )

    def pair(self, key: PairKey) -> Mapping[str, EvidenceCell]:
        direct = self.pairs.get(key)
        if direct is not None:
            return direct
        # Long-lived callers can retain an EvidenceBundle across a module
        # reload. Dataclass identities then differ even though every key field
        # is unchanged, so fall back to a primitive-field match.
        for candidate, pair in self.pairs.items():
            if (
                candidate.split == key.split
                and candidate.scenario_id == key.scenario_id
                and candidate.model == key.model
                and candidate.seed == key.seed
            ):
                return pair
        raise KeyError(f"no formal pair for {key.label}")


def load_evidence(
    manifest_path: str | Path = DEFAULT_MANIFEST,
    *,
    verify_hashes: bool = True,
) -> EvidenceBundle:
    """Load complete cells declared by the final evidence manifest.

    Hash verification covers every declared formal cell file. Other manifest
    entries remain available through the evidence package's separate verifier.
    """

    path = Path(manifest_path).resolve()
    root = _find_root(path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    declared = [item for item in manifest.get("files", []) if item.get("kind") == "cells"]
    if not declared:
        raise ValueError("evidence manifest declares no formal cell files")
    store = _EvidenceStore(root, manifest)

    verification = _verify_files(store, declared) if verify_hashes else VerificationResult(
        checked=0, valid=True, errors=()
    )
    if not verification.valid:
        joined = "; ".join(verification.errors)
        raise ValueError(f"formal cell verification failed: {joined}")

    cells: list[EvidenceCell] = []
    cells_by_id: dict[str, EvidenceCell] = {}
    for source in declared:
        split = str(source.get("split", "")).strip()
        if not split:
            raise ValueError(f"cell source lacks split: {source.get('path')}")
        relative = str(source["path"])
        records = list(_read_jsonl(store.read_bytes(relative), relative))
        expected_records = source.get("records")
        if expected_records is not None and len(records) != int(expected_records):
            raise ValueError(
                f"{source['path']} has {len(records)} records; "
                f"manifest declares {expected_records}"
            )
        for payload in records:
            if not bool(payload.get("complete", False)):
                continue
            cell = EvidenceCell(payload=payload, source=str(source["path"]), split=split)
            if cell.cell_id in cells_by_id:
                raise ValueError(f"duplicate formal cell id: {cell.cell_id}")
            cells.append(cell)
            cells_by_id[cell.cell_id] = cell

    expected_cells = int(manifest.get("cells", -1))
    if len(cells) != expected_cells:
        raise ValueError(
            f"loaded {len(cells)} complete cells; manifest declares {expected_cells}"
        )

    pair_index: dict[PairKey, dict[str, EvidenceCell]] = {}
    for cell in cells:
        method_map = pair_index.setdefault(cell.pair_key, {})
        if cell.method in method_map:
            raise ValueError(
                f"duplicate method {cell.method!r} for pair {cell.pair_key.label}"
            )
        method_map[cell.method] = cell

    return EvidenceBundle(
        root=root,
        manifest=manifest,
        cells=tuple(cells),
        cells_by_id=cells_by_id,
        pairs={key: dict(value) for key, value in pair_index.items()},
        verification=verification,
    )


def load_statistics(path: str | Path = DEFAULT_STATISTICS) -> Mapping[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def events_for_cell(cell: EvidenceCell) -> tuple[EvidenceEvent, ...]:
    """Build a concise, de-duplicated event index for one episode."""

    events: dict[tuple[int, str, str], EvidenceEvent] = {}

    def add(day: int, kind: str, label: str, detail: str) -> None:
        event = EvidenceEvent(day=int(day), kind=kind, label=label, detail=detail)
        events[(event.day, event.kind, event.label)] = event

    if cell.shift_day is not None:
        add(
            cell.shift_day,
            "regime",
            "Regime changed",
            "The scenario's declared environment shift begins here.",
        )

    for review in cell.payload.get("review_logs", []):
        day = int(review["day"])
        trigger = str(review.get("trigger_reason", "review"))
        kind = "review_event" if trigger == "event" else "review_periodic"
        label = "Event review" if trigger == "event" else "Periodic review"
        proposal = review.get("proposal") or {}
        detail = str(proposal.get("reason", "Strategy review recorded."))
        add(day, kind, label, detail)
        if bool(review.get("fallback_used", False)):
            add(
                day,
                "fallback",
                "Retained-strategy fallback",
                "The provider attempt failed and the previous validated strategy remained active.",
            )

    memory_audit = cell.payload.get("memory_audit") or {}
    for record in memory_audit.get("records", []):
        memory_id = str(record.get("memory_id", "memory"))
        for audit in record.get("audit_events", []):
            old = str(audit.get("old_status", "unknown"))
            new = str(audit.get("new_status", "unknown"))
            reason = str(audit.get("reason", "lifecycle update"))
            variable = audit.get("variable")
            detail = f"{memory_id}: {old} → {new} because {reason}"
            if variable:
                detail += f" ({variable})"
            add(int(audit["step"]), "memory", "Memory lifecycle", detail)

    for row in cell.payload.get("environment_records", []):
        lost = int(row.get("lost_sales", 0))
        if lost > 0:
            add(
                int(row["day"]),
                "stockout",
                "Lost sales",
                f"{lost} unit{'s' if lost != 1 else ''} of demand were not served.",
            )

    return tuple(sorted(events.values(), key=lambda event: event.sort_key))


def day_snapshot(cell: EvidenceCell, day: int) -> Mapping[str, Any]:
    """Return the synchronized records used by the day inspector."""

    if day < 0 or day >= cell.days:
        raise ValueError(f"day {day} is outside the cell's 0–{cell.days - 1} range")
    environment = _record_for_day(cell.payload.get("environment_records", []), day)
    decision = _record_for_day(cell.payload.get("daily_decision_log", []), day)
    scheduler = _record_for_day(cell.payload.get("scheduler_log", []), day)
    reviews = tuple(
        row for row in cell.payload.get("review_logs", []) if int(row["day"]) == day
    )
    return {
        "environment": environment,
        "decision": decision,
        "scheduler": scheduler,
        "reviews": reviews,
    }


def memory_records(cell: EvidenceCell) -> tuple[Mapping[str, Any], ...]:
    audit = cell.payload.get("memory_audit") or {}
    return tuple(audit.get("records", []))


def cited_memories(cell: EvidenceCell, day: int) -> tuple[Mapping[str, Any], ...]:
    reviews = [
        row for row in cell.payload.get("review_logs", []) if int(row["day"]) == day
    ]
    cited_ids = {
        str(memory_id)
        for review in reviews
        for memory_id in review.get("cited_memory_ids", [])
    }
    return tuple(
        record
        for record in memory_records(cell)
        if str(record.get("memory_id")) in cited_ids
    )


def next_event_day(events: Iterable[EvidenceEvent], day: int, *, forward: bool) -> int:
    days = sorted({event.day for event in events})
    if not days:
        return day
    if forward:
        return next((candidate for candidate in days if candidate > day), days[-1])
    return next((candidate for candidate in reversed(days) if candidate < day), days[0])


def _record_for_day(records: Iterable[Mapping[str, Any]], day: int) -> Mapping[str, Any]:
    return next((row for row in records if int(row.get("day", -1)) == day), {})


def _read_jsonl(content: bytes, source: str) -> Iterator[dict[str, Any]]:
    for line_number, line in enumerate(content.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{source}:{line_number} is not a JSON object")
        yield payload


class _EvidenceStore:
    """Read manifest-declared evidence from local runs or the frozen release.

    Formal raw-run directories are intentionally ignored by Git. A clean clone
    therefore falls back to the tracked, read-only release archive and verifies
    both the archive checksum and each manifest-declared file checksum before
    exposing any record to the Demo.
    """

    def __init__(self, root: Path, manifest: Mapping[str, Any]) -> None:
        self.root = root
        self.freeze_id = str(manifest.get("evidence_freeze_id", "")).strip()
        self._cache: dict[str, bytes] = {}
        self._archive_verified = False

    def read_bytes(self, relative: str) -> bytes:
        cached = self._cache.get(relative)
        if cached is not None:
            return cached

        local_path = self.root / relative
        if local_path.exists():
            content = local_path.read_bytes()
        else:
            content = self._read_archive_member(relative)
        self._cache[relative] = content
        return content

    def _read_archive_member(self, relative: str) -> bytes:
        archive_path = self._archive_path()
        self._verify_archive(archive_path)
        member = Path(relative).name
        try:
            with ZipFile(archive_path) as archive:
                return archive.read(member)
        except KeyError as exc:
            raise FileNotFoundError(
                f"{relative} is absent locally and {member} is absent from "
                f"{archive_path.relative_to(self.root)}"
            ) from exc
        except BadZipFile as exc:
            raise ValueError(f"invalid evidence archive: {archive_path}") from exc

    def _archive_path(self) -> Path:
        if not self.freeze_id:
            raise FileNotFoundError("manifest has no evidence_freeze_id for archive fallback")
        return (
            self.root
            / "artifacts"
            / "releases"
            / f"{self.freeze_id}-raw-evidence.zip"
        )

    def _verify_archive(self, archive_path: Path) -> None:
        if self._archive_verified:
            return
        checksum_path = archive_path.with_name(
            f"{self.freeze_id}-raw-evidence.sha256.json"
        )
        if not archive_path.exists() or not checksum_path.exists():
            raise FileNotFoundError(
                f"missing release archive or checksum for {self.freeze_id}"
            )
        checksum = json.loads(checksum_path.read_text(encoding="utf-8"))
        if checksum.get("evidence_freeze_id") != self.freeze_id:
            raise ValueError("release checksum freeze id does not match the manifest")
        expected_bytes = int(checksum.get("archive_bytes", -1))
        if archive_path.stat().st_size != expected_bytes:
            raise ValueError("release archive byte count does not match its checksum record")
        expected_hash = str(checksum.get("archive_sha256", ""))
        if _sha256(archive_path) != expected_hash:
            raise ValueError("release archive SHA-256 does not match its checksum record")
        self._archive_verified = True


def _verify_files(
    store: _EvidenceStore,
    declared: Iterable[Mapping[str, Any]],
) -> VerificationResult:
    errors: list[str] = []
    checked = 0
    for item in declared:
        relative = str(item["path"])
        try:
            content = store.read_bytes(relative)
        except (FileNotFoundError, OSError, ValueError) as exc:
            errors.append(f"missing or invalid {relative}: {exc}")
            continue
        digest = hashlib.sha256(content).hexdigest()
        checked += 1
        expected = str(item.get("sha256", ""))
        if digest != expected:
            errors.append(f"hash mismatch for {relative}")
    return VerificationResult(
        checked=checked,
        valid=not errors,
        errors=tuple(errors),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_root(manifest_path: Path) -> Path:
    for parent in (manifest_path.parent, *manifest_path.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    raise ValueError(f"could not locate repository root from {manifest_path}")


def _split_sort_key(split: str) -> tuple[int, str]:
    order = {"Test-ID": 0, "Test-OOD": 1}
    return (order.get(split, 99), split)
