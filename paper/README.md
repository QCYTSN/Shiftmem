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
| [`ShiftMem.pdf`](ShiftMem.pdf) | Compiled 14-page manuscript snapshot |
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

## Read the paper

[**Download the compiled PDF**](ShiftMem.pdf)

The tracked PDF is an unencrypted 14-page snapshot compiled from this source
package. Its SHA-256 digest is
`2c4083ea085822e5d40269e38b40f77ec93bcfae03ca5affbd4cc6f737ed7bc4`.
The LaTeX source remains the editable and reproducible form of the manuscript.

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

## License

The repository's MIT License applies to the software source code, not to the
scholarly content in this directory. The manuscript, compiled PDF, figures,
tables, bibliography, and related paper materials remain copyright © 2026
Fengkai Gao, all rights reserved. See [`LICENSE`](LICENSE).
