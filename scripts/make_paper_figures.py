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
from matplotlib.lines import Line2D
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


def add_arrow(
    axis: Any,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str = NEUTRAL,
    *,
    linestyle: str = "-",
    connectionstyle: str = "arc3",
) -> None:
    axis.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=0.8,
            color=color,
            linestyle=linestyle,
            connectionstyle=connectionstyle,
            transform=axis.transAxes,
        )
    )


def make_architecture_figure(output_base: Path) -> None:
    figure, axis = plt.subplots(figsize=(7.2, 3.1))
    axis.set_axis_off()
    add_box(axis, 0.02, 0.54, 0.15, 0.22, "Public inventory\nhistory", NEUTRAL)
    add_box(axis, 0.22, 0.69, 0.14, 0.17, "Change\ndetector", NEUTRAL)
    add_box(axis, 0.22, 0.40, 0.14, 0.17, "Review\nscheduler", NEUTRAL)
    add_box(axis, 0.42, 0.54, 0.16, 0.20, "Conditional\nmemory retrieval", METHOD_COLORS["ShiftMem"])
    add_box(axis, 0.62, 0.54, 0.15, 0.20, "Bounded LLM\nstrategy review", ACCENT)
    add_box(axis, 0.81, 0.54, 0.13, 0.20, "Schema and\nbounds", ACCENT)
    add_box(axis, 0.81, 0.25, 0.13, 0.17, "Deterministic\ndaily controller", NEUTRAL)
    add_box(axis, 0.62, 0.08, 0.15, 0.17, "Inventory\noutcome", NEUTRAL)
    add_box(axis, 0.42, 0.08, 0.16, 0.17, "Delayed validation\nand lifecycle audit", METHOD_COLORS["ShiftMem"])
    add_arrow(axis, (0.17, 0.68), (0.22, 0.77))
    add_arrow(axis, (0.17, 0.60), (0.22, 0.49))
    add_arrow(axis, (0.29, 0.69), (0.29, 0.57))
    add_arrow(axis, (0.36, 0.49), (0.42, 0.64))
    add_arrow(axis, (0.58, 0.64), (0.62, 0.64))
    add_arrow(axis, (0.77, 0.64), (0.81, 0.64))
    add_arrow(axis, (0.875, 0.54), (0.875, 0.42))
    add_arrow(axis, (0.81, 0.33), (0.77, 0.18))
    add_arrow(axis, (0.62, 0.17), (0.58, 0.17))
    add_arrow(axis, (0.50, 0.25), (0.50, 0.54))
    add_arrow(axis, (0.36, 0.78), (0.47, 0.74), linestyle="--")
    axis.text(
        0.50,
        0.94,
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
        "Agent-facing paths use public observations; hidden regime labels and Oracle context remain outside the agent",
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
        ("Overall", endpoint["overall"], "prespecified confirmatory, dependence-limited"),
        ("Test-ID", endpoint["by_split"]["Test-ID"], "prespecified descriptive"),
        ("Test-OOD", endpoint["by_split"]["Test-OOD"], "prespecified descriptive"),
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
            "test_method": str(result["test"]["method"]),
            "p_value": float(result["test"]["p_value"]),
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
                "test_method": str(result["test"]["method"]),
                "p_value": float(result["test"]["p_value"]),
                "status": "descriptive subgroup",
            }
        )
    figure, axes = plt.subplots(1, 2, figsize=(7.2, 3.9), gridspec_kw={"width_ratios": [1.0, 1.35]})
    for axis, panel_rows, title in zip(axes, [rows, scenario_rows], ["Primary and model splits", "Scenario decomposition"]):
        positions = list(range(len(panel_rows)))
        for position, row in zip(positions, panel_rows):
            color = NEUTRAL if row["group"] == "Overall" else ACCENT if row["mean_difference"] > 0 else METHOD_COLORS["ShiftMem"]
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
    axes[0].text(-0.12, 1.04, "a", transform=axes[0].transAxes, fontsize=9, fontweight="bold")
    axes[1].text(-0.12, 1.04, "b", transform=axes[1].transAxes, fontsize=9, fontweight="bold")
    figure.tight_layout(w_pad=2.0)
    save_figure(figure, output_base)
    return rows + scenario_rows


def make_reliability_figure(reliability: dict[str, Any], output_base: Path) -> list[dict[str, Any]]:
    rows = reliability["by_split_model_method"]
    groups = [
        ("deepseek", "shiftmem", "DeepSeek\nShiftMem"),
        ("deepseek", "vector", "DeepSeek\nLexical"),
        ("minimax", "shiftmem", "MiniMax\nShiftMem"),
        ("minimax", "vector", "MiniMax\nLexical"),
    ]
    values_by_split: dict[str, list[dict[str, Any]]] = {}
    for split in ("Test-ID", "Test-OOD"):
        split_rows = []
        for model, method, _ in groups:
            split_rows.append(
                next(
                    row
                    for row in rows
                    if row["split"] == split and row["model"] == model and row["method"] == method
                )
            )
        values_by_split[split] = split_rows
    figure, axes = plt.subplots(1, 3, figsize=(7.2, 2.7), sharex=True)
    panels = [
        (lambda row: 100 * float(row["parse_failures_per_attempt"]), "Failed/invalid attempts", "% of attempts", "#b45f48"),
        (lambda row: 100 * float(row["fallbacks_per_review"]), "Retained strategy", "% of reviews", "#8a6a3d"),
        (lambda row: float(row["input_tokens"]) / float(row["reviews"]), "Input context", "tokens per review", "#315f86"),
    ]
    split_style = {
        "Test-ID": {"marker": "o", "offset": -0.11, "label": "Test-ID"},
        "Test-OOD": {"marker": "s", "offset": 0.11, "label": "Test-OOD"},
    }
    for panel_index, (axis, (metric, title, ylabel, color)) in enumerate(zip(axes, panels)):
        for split, style in split_style.items():
            values = [metric(row) for row in values_by_split[split]]
            positions = [index + style["offset"] for index in range(len(groups))]
            axis.scatter(
                positions,
                values,
                s=28,
                marker=style["marker"],
                facecolor=color if split == "Test-ID" else "white",
                edgecolor=color,
                linewidth=1.0,
                zorder=3,
            )
        axis.set_title(title, loc="left", fontsize=8, fontweight="bold")
        axis.set_ylabel(ylabel)
        axis.set_xticks(range(len(groups)))
        axis.set_xticklabels([label for _, _, label in groups], fontsize=6)
        axis.grid(axis="y", color="#d9dde2", linewidth=0.45)
        axis.set_axisbelow(True)
        axis.text(-0.15, 1.04, chr(ord("a") + panel_index), transform=axis.transAxes, fontsize=9, fontweight="bold")
    axes[2].legend(
        handles=[
            Line2D([0], [0], marker="o", color="none", markerfacecolor=NEUTRAL, markeredgecolor=NEUTRAL, label="Test-ID"),
            Line2D([0], [0], marker="s", color="none", markerfacecolor="white", markeredgecolor=NEUTRAL, label="Test-OOD"),
        ],
        loc="upper right",
        fontsize=6,
    )
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


def effect_display_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "group": row["group"],
            "difference": f"{row['mean_difference']:.2f}",
            "nominal 95% CI": f"[{row['ci_low']:.2f}, {row['ci_high']:.2f}]",
            "n": row["n"],
            "test": row["test_method"],
            "p": f"{row['p_value']:.3f}",
            "status": row["status"],
        }
        for row in rows
    ]


def reliability_display_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "split": row["split"],
            "model": "DeepSeek" if row["model"] == "deepseek" else "MiniMax",
            "method": "ShiftMem" if row["method"] == "shiftmem" else "Lexical baseline",
            "cells": row["cells"],
            "attempts": row["provider_attempts_recorded_by_cells"],
            "failed/invalid attempts": row["parse_failures"],
            "failed/invalid rate": f"{100 * row['parse_failures_per_attempt']:.1f}%",
            "reviews": row["reviews"],
            "fallbacks": row["fallbacks"],
            "fallback rate": f"{100 * row['fallbacks_per_review']:.1f}%",
            "input tokens": row["input_tokens"],
            "output tokens": row["output_tokens"],
            "recovered": f"{row['recovered_cells']}/{row['applicable_recovery_cells']}",
        }
        for row in rows
    ]


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
    write_markdown_table(
        tables_dir / "table_2_effects.md",
        "Primary and descriptive effects",
        effect_display_rows(effect_rows),
    )
    write_csv(tables_dir / "table_3_reliability.csv", reliability_rows)
    write_markdown_table(
        tables_dir / "table_3_reliability.md",
        "Reliability and context burden",
        reliability_display_rows(reliability_rows),
    )
    write_protocol_table(tables_dir / "table_1_protocol", manifest, stats)


if __name__ == "__main__":
    main()
