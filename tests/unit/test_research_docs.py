from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_related_work_matrix_has_required_columns_and_scope() -> None:
    text = (ROOT / "docs/related_work_matrix.md").read_text(encoding="utf-8")
    header = next(line for line in text.splitlines() if line.startswith("| Work |"))
    for column in (
        "Problem",
        "Memory unit",
        "Change assumption",
        "Retrieval",
        "Validation",
        "Lifecycle",
        "Environment",
        "Metrics",
        "Limitations",
        "ShiftMem distinction",
    ):
        assert f"| {column} " in header
    data_rows = [
        line
        for line in text.splitlines()
        if line.startswith("|") and "---" not in line and not line.startswith("| Work |")
    ]
    assert len(data_rows) >= 12
    for topic in ("Agent memory", "Concept drift", "Inventory", "Enterprise agent"):
        assert topic in text


def test_related_work_uses_primary_links_and_avoids_novelty_claims() -> None:
    text = (ROOT / "docs/related_work_matrix.md").read_text(encoding="utf-8")
    assert text.count("https://arxiv.org/abs/") >= 8
    assert "https://doi.org/" in text
    assert "https://aclanthology.org/" in text
    lower = text.lower()
    assert "first-ever" not in lower
    assert "state-of-the-art" not in lower
    assert "shiftmem is the first" not in lower


def test_bibliography_contains_matrix_citation_keys() -> None:
    bib = (ROOT / "paper/references.bib").read_text(encoding="utf-8")
    for key in (
        "park2023generative",
        "shinn2023reflexion",
        "packer2023memgpt",
        "bifet2007adwin",
        "treharne2002adaptive",
        "drouin2024workarena",
    ):
        assert f"{{{key}," in bib


def test_live_research_docs_report_post_freeze_status() -> None:
    audit_path = ROOT / "docs/formal_experiment_readiness_audit.md"
    assert audit_path.exists(), "live formal-readiness audit is missing"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    implementation_log = (ROOT / "docs/implementation_log.md").read_text(
        encoding="utf-8"
    )
    pilot = (ROOT / "docs/phase4_pilot_report.md").read_text(encoding="utf-8")
    audit = audit_path.read_text(encoding="utf-8")

    docs_index = (ROOT / "docs/README.md").read_text(encoding="utf-8")
    model_card = (ROOT / "docs/model_card.md").read_text(encoding="utf-8")

    assert "v2-formal-results-f4ab41daacf3" in readme
    assert "H1 not supported" in readme
    assert "MiniMaxAI/MiniMax-M2.5" in model_card
    assert "Protocol v1.1 live Validation report" in docs_index
    assert "fixed-policy pre-shift warm-up" in pilot
    assert "pre-seeded memories" in pilot
    assert "Detector-selection/runtime mismatch" in audit
    assert "Hypothesis coverage gaps" in audit
    assert "Test-ID and Test-OOD outcomes must not be generated or read" in audit
    assert "Post-freeze readiness audit" in implementation_log
    assert "the planned two-model formal design is not yet frozen" not in readme
    assert "Planned structure" not in readme


def test_v1_1_docs_preserve_live_validation_limit_and_budget_blocker() -> None:
    report_path = ROOT / "docs/v1_1_live_validation_report.md"
    assert report_path.exists(), "v1.1 live Validation report is missing"
    protocol = (ROOT / "docs/experiment_protocol.md").read_text(encoding="utf-8")
    report = report_path.read_text(encoding="utf-8")
    audit = (ROOT / "docs/formal_experiment_readiness_audit.md").read_text(
        encoding="utf-8"
    )

    assert "Protocol version: 1.1" in protocol
    assert "quoted_lead_time" in protocol
    assert "168,480" in protocol
    assert "historical unjournaled failed attempts: 6" in report.lower()
    assert "CNY 1,506.22" in report
    assert "formal API budget approval" in audit
