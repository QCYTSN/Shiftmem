# ShiftMem manuscript

## Title

**Does Conditional Memory Help an LLM Inventory Agent under Regime Shifts?<br>
A Systems Evaluation Frozen before Test-Outcome Access**

This directory contains the complete manuscript source accompanying the frozen
ShiftMem Protocol-v2 evaluation. The paper reports the negative primary result,
dependence-aware sensitivity analysis, descriptive heterogeneity, reliability
audit, limitations, and the content-addressed evidence workflow.

The repository contains manuscript source, not a claim of journal acceptance or
peer review.

## Contents

| Path | Purpose |
| --- | --- |
| [`main.tex`](main.tex) | Document entry point and author metadata |
| [`abstract.tex`](abstract.tex) | Abstract |
| [`introduction.tex`](introduction.tex) | Motivation and contributions |
| [`related_work.tex`](related_work.tex) | Related work |
| [`method.tex`](method.tex) | ShiftMem architecture and evaluation design |
| [`experiments.tex`](experiments.tex) | Formal results and reliability analyses |
| [`conclusion.tex`](conclusion.tex) | Interpretation, limits, and follow-up controls |
| [`availability.tex`](availability.tex) | Code and data availability statement |
| [`appendices.tex`](appendices.tex) | Extended protocol and audit details |
| [`references.bib`](references.bib) | BibTeX references |
| [`figures/`](figures/) | Publication figures in PDF, SVG, PNG, and TIFF |
| [`tables/`](tables/) | Table source data and LaTeX renderings |

## Build

A full LaTeX distribution such as TeX Live or MiKTeX is required. From the
repository root:

```powershell
cd paper
latexmk -pdf main.tex
```

If `latexmk` is unavailable, use the equivalent explicit sequence:

```powershell
cd paper
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

The generated PDF and LaTeX build intermediates are intentionally ignored by
Git. For Overleaf, upload the contents of this directory and keep `main.tex` as
the main document.

## Reproduce the figures and evidence

Paper figures are generated from frozen aggregate outputs:

```powershell
python scripts/make_paper_figures.py
```

The formal evidence can be checked without network access or provider
credentials:

```powershell
python -m pytest -q
python scripts/verify_release_archive.py
python scripts/finalize_formal_results.py --verify
```

Authoritative result files:

- [Evidence manifest](../artifacts/aggregated/v2_formal_evidence_manifest.json)
- [Formal statistical analysis](../artifacts/aggregated/v2_formal_statistical_analysis.json)
- [Reliability audit](../artifacts/aggregated/v2_formal_reliability_audit.json)
- [Formal post-Test audit](../docs/v2_formal_post_test_audit.md)

The formal closure identity is `v2-formal-results-f4ab41daacf3`.
