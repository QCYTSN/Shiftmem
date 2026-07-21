import pytest

from shiftmem.evaluation.statistics import (
    holm_adjust,
    paired_analysis,
    paired_summary,
    paired_t_test,
    wilcoxon_signed_rank,
)


def test_paired_summary_reports_difference_interval_and_effect_size() -> None:
    result = paired_summary([(10, 12), (8, 10), (9, 12)])

    assert result["n"] == 3
    assert result["mean_difference"] == pytest.approx(-7 / 3)
    assert result["sd_difference"] == pytest.approx(3 ** -0.5)
    assert result["effect_size_dz"] == pytest.approx((-7 / 3) / (3 ** -0.5))
    assert result["ci_low"] < result["mean_difference"] < result["ci_high"]


def test_paired_t_test_handles_constant_nonzero_difference() -> None:
    result = paired_t_test([2.0, 2.0, 2.0])

    assert result["statistic"] == float("inf")
    assert result["p_value"] == 0.0


def test_wilcoxon_exact_two_sided_probability_for_three_positive_ranks() -> None:
    result = wilcoxon_signed_rank([1.0, 2.0, 3.0])

    assert result["statistic"] == 0.0
    assert result["p_value"] == pytest.approx(0.25)
    assert result["method"] == "wilcoxon_signed_rank_exact"


def test_holm_adjustment_preserves_order_and_is_monotone_by_rank() -> None:
    assert holm_adjust([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_paired_analysis_uses_signed_rank_for_severe_outlier_pattern() -> None:
    pairs = [(value, 0.0) for value in [0, 0, 0, 0, 0, 0, 1, 100]]

    result = paired_analysis(pairs)

    assert result["severe_outlier"] is True
    assert str(result["test"]["method"]).startswith("wilcoxon_signed_rank")
