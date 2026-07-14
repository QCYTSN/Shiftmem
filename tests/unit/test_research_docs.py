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
