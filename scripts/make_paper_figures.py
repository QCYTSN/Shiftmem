"""Generate fact-grounded paper figures and source tables from the v2 closure."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from shiftmem.evaluation.post_test import load_declared_cells, verify_declared_sources


EVIDENCE_ID = "v2-formal-results-f4ab41daacf3"
METHOD_COLORS = {"ShiftMem": "#315f86", "Lexical baseline": "#8a8f98"}
ACCENT = "#b45f48"
NEUTRAL = "#53606e"


def configure_matplotlib() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.frameon": False,
        }
    )


def load_evidence(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    manifest_path = root / "artifacts" / "aggregated" / "v2_formal_evidence_manifest.json"
    stats_path = root / "artifacts" / "aggregated" / "v2_formal_statistical_analysis.json"
    reliability_path = root / "artifacts" / "aggregated" / "v2_formal_reliability_audit.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["evidence_freeze_id"] != EVIDENCE_ID:
        raise ValueError(f"unexpected evidence closure: {manifest['evidence_freeze_id']}")
    verify_declared_sources(root, manifest["files"])
    cells, _ = load_declared_cells(root, manifest["files"])
    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    reliability = json.loads(reliability_path.read_text(encoding="utf-8"))
    if stats["evidence_freeze_id"] != EVIDENCE_ID or reliability["evidence_freeze_id"] != EVIDENCE_ID:
        raise ValueError("derived output does not match the evidence closure")
    return manifest, cells, stats, reliability


def save_figure(figure: plt.Figure, output_base: Path) -> None:
    output_base.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_base.with_suffix(".svg"), bbox_inches="tight")
    figure.savefig(output_base.with_suffix(".pdf"), bbox_inches="tight")
    figure.savefig(output_base.with_suffix(".png"), dpi=600, bbox_inches="tight")
    figure.savefig(output_base.with_suffix(".tiff"), dpi=600, bbox_inches="tight")
    plt.close(figure)


def add_box(axis: Any, x: float, y: float, width: float, height: float, text: str, color: str) -> None:
    axis.add_patch(
        FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.012,rounding_size=0.015",
            linewidth=0.9,
            edgecolor=color,
            facecolor="#f7f8fa",
            transform=axis.transAxes,
        )
    )
    axis.text(
        x + width / 2,
        y + height / 2,
        text,
        ha="center",
        va="center",
        color="#1f2933",
        transform=axis.transAxes,
    )


def add_arrow(axis: Any, start: tuple[float, float], end: tuple[float, float], color: str = NEUTRAL) -> None:
    axis.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=0.8,
            color=color,
            transform=axis.transAxes,
        )
    )


def make_architecture_figure(output_base: Path) -> None:
    figure, axis = plt.subplots(figsize=(7.2, 3.1))
    axis.set_axis_off()
    add_box(axis, 0.02, 0.39, 0.15, 0.22, "Public inventory\nhistory", NEUTRAL)
    add_box(axis, 0.23, 0.62, 0.16, 0.20, "Change\ndetector", NEUTRAL)
    add_box(axis, 0.23, 0.27, 0.16, 0.20, "Review\nscheduler", NEUTRAL)
    add_box(axis, 0.45, 0.27, 0.16, 0.20, "Conditional\nmemory retrieval", METHOD_COLORS["ShiftMem"])
    add_box(axis, 0.45, 0.62, 0.16, 0.20, "Bounded LLM\nstrategy review", ACCENT)
    add_box(axis, 0.67, 0.62, 0.14, 0.20, "Schema and\nbounds", ACCENT)
    add_box(axis, 0.84, 0.39, 0.14, 0.22, "Deterministic\ncontroller", NEUTRAL)
    add_box(axis, 0.84, 0.06, 0.14, 0.17, "Daily order\nand outcome", NEUTRAL)
    add_box(axis, 0.45, 0.02, 0.16, 0.17, "Delayed validation\nand lifecycle audit", METHOD_COLORS["ShiftMem"])
    add_arrow(axis, (0.17, 0.50), (0.23, 0.69))
    add_arrow(axis, (0.17, 0.48), (0.23, 0.37))
    add_arrow(axis, (0.39, 0.37), (0.45, 0.37))
    add_arrow(axis, (0.39, 0.69), (0.45, 0.69))
    add_arrow(axis, (0.53, 0.62), (0.53, 0.47))
    add_arrow(axis, (0.61, 0.69), (0.67, 0.69))
    add_arrow(axis, (0.81, 0.69), (0.84, 0.52))
    add_arrow(axis, (0.91, 0.39), (0.91, 0.23))
    add_arrow(axis, (0.84, 0.15), (0.61, 0.10))
    add_arrow(axis, (0.53, 0.19), (0.53, 0.27))
    axis.text(
        0.50,
        0.91,
        "LLM proposes strategy parameters; it never emits the daily order",
        ha="center",
        va="center",
        fontsize=8,
        fontweight="bold",
        transform=axis.transAxes,
    )
    axis.text(
        0.50,
        -0.03,
        "All arrows use public observations; hidden regime labels and Oracle context remain outside the agent",
        ha="center",
        va="top",
        fontsize=6.5,
        color="#53606e",
        transform=axis.transAxes,
    )
    save_figure(figure, output_base)


def forest_rows(stats: dict[str, Any]) -> list[dict[str, Any]]:
    endpoint = stats["primary_endpoint"]
    rows = [
        ("Overall", endpoint["overall"], "confirmatory"),
        ("Test-ID", endpoint["by_split"]["Test-ID"], "predeclared descriptive"),
        ("Test-OOD", endpoint["by_split"]["Test-OOD"], "predeclared descriptive"),
        ("DeepSeek", endpoint["by_model"]["deepseek"], "unadjusted descriptive"),
        ("MiniMax", endpoint["by_model"]["minimax"], "unadjusted descriptive"),
    ]
    return [
        {
            "group": name,
            "mean_difference": float(result["mean_difference"]),
            "ci_low": float(result["ci_low"]),
            "ci_high": float(result["ci_high"]),
            "n": int(result["n"]),
            "status": status,
        }
        for name, result, status in rows
    ]


def make_effect_figure(stats: dict[str, Any], output_base: Path) -> list[dict[str, Any]]:
    endpoint = stats["primary_endpoint"]
    rows = forest_rows(stats)
    scenario_rows = []
    for scenario, result in endpoint["by_scenario"].items():
        scenario_rows.append(
            {
                "group": scenario.replace("test-id-", "ID: ").replace("test-ood-", "OOD: "),
                "mean_difference": float(result["mean_difference"]),
                "ci_low": float(result["ci_low"]),
                "ci_high": float(result["ci_high"]),
                "n": int(result["n"]),
                "status": "descriptive subgroup",
            }
        )
    figure, axes = plt.subplots(1, 2, figsize=(7.2, 3.9), gridspec_kw={"width_ratios": [1.0, 1.35]})
    for axis, panel_rows, title in zip(axes, [rows, scenario_rows], ["Primary and model splits", "Scenario decomposition"]):
        positions = list(range(len(panel_rows)))
        for position, row in zip(positions, panel_rows):
            color = NEUTRAL if row["status"] == "confirmatory" else ACCENT if row["mean_difference"] > 0 else METHOD_COLORS["ShiftMem"]
            axis.errorbar(
                row["mean_difference"],
                position,
                xerr=[[row["mean_difference"] - row["ci_low"]], [row["ci_high"] - row["mean_difference"]]],
                fmt="o",
                color=color,
                markersize=4.5,
                capsize=2.5,
                linewidth=1.1,
            )
        axis.axvline(0, color="#30343b", linewidth=0.8, linestyle="--")
        axis.set_yticks(positions)
        axis.set_yticklabels([f"{row['group']} (n={row['n']})" for row in panel_rows])
        axis.invert_yaxis()
        axis.set_title(title, loc="left", fontsize=8, fontweight="bold")
        axis.set_xlabel("ShiftMem - lexical baseline\nnegative favors ShiftMem")
        axis.grid(axis="x", color="#d9dde2", linewidth=0.45)
        axis.set_axisbelow(True)
    figure.tight_layout(w_pad=2.0)
    save_figure(figure, output_base)
    return rows + scenario_rows


def make_reliability_figure(reliability: dict[str, Any], output_base: Path) -> list[dict[str, Any]]:
    rows = reliability["by_split_model_method"]
    labels = [f"{row['split']}\n{row['model']}\n{row['method']}" for row in rows]
    parse_rates = [100 * float(row["parse_failures_per_attempt"]) for row in rows]
    fallback_rates = [100 * float(row["fallbacks_per_review"]) for row in rows]
    tokens_per_review = [float(row["input_tokens"]) / float(row["reviews"]) for row in rows]
    figure, axes = plt.subplots(1, 3, figsize=(7.2, 2.7), sharex=True)
    panels = [
        (parse_rates, "Parse failures", "% of attempts", "#b45f48"),
        (fallback_rates, "Retained strategy", "% of reviews", "#8a6a3d"),
        (tokens_per_review, "Input context", "tokens per review", "#315f86"),
    ]
    for axis, (values, title, ylabel, color) in zip(axes, panels):
        axis.scatter(range(len(values)), values, s=25, color=color, zorder=3)
        axis.set_title(title, loc="left", fontsize=8, fontweight="bold")
        axis.set_ylabel(ylabel)
        axis.set_xticks(range(len(labels)))
        axis.set_xticklabels(labels, rotation=60, ha="right", fontsize=5.5)
        axis.grid(axis="y", color="#d9dde2", linewidth=0.45)
        axis.set_axisbelow(True)
    figure.suptitle("Reliability and context burden in the complete 160-cell matrix", x=0.02, ha="left", fontsize=8.5, fontweight="bold")
    figure.tight_layout(rect=(0, 0, 1, 0.91))
    save_figure(figure, output_base)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown_table(path: Path, title: str, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = list(rows[0]) if rows else []
    lines = [f"# {title}", "", "| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(row[header]) for header in headers) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_protocol_table(path: Path, manifest: dict[str, Any], stats: dict[str, Any]) -> None:
    rows = [
        {
            "evidence_freeze": manifest["evidence_freeze_id"],
            "complete_cells": manifest["cells"],
            "models": "DeepSeek-V3.2; MiniMax-M2.5",
            "methods": "ShiftMem; lexical retrieval baseline",
            "scenarios": 8,
            "seeds_per_scenario": 5,
            "primary_units": stats["primary_endpoint"]["overall"]["n"],
            "endpoint": stats["primary_endpoint"]["reporting_label"],
        }
    ]
    write_csv(path.with_suffix(".csv"), rows)
    write_markdown_table(path.with_suffix(".md"), "Frozen evaluation protocol", rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("paper/figures"))
    parser.add_argument("--tables-dir", type=Path, default=Path("paper/tables"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    configure_matplotlib()
    manifest, _, stats, reliability = load_evidence(root)
    output_dir = root / args.output_dir
    tables_dir = root / args.tables_dir
    effect_rows = make_effect_figure(stats, output_dir / "figure_2_effect_forest")
    reliability_rows = make_reliability_figure(reliability, output_dir / "figure_3_reliability")
    make_architecture_figure(output_dir / "figure_1_architecture")
    write_csv(tables_dir / "table_2_effects.csv", effect_rows)
    write_markdown_table(tables_dir / "table_2_effects.md", "Primary and descriptive effects", effect_rows)
    write_csv(tables_dir / "table_3_reliability.csv", reliability_rows)
    write_markdown_table(tables_dir / "table_3_reliability.md", "Reliability and context burden", reliability_rows)
    write_protocol_table(tables_dir / "table_1_protocol", manifest, stats)


if __name__ == "__main__":
    main()
