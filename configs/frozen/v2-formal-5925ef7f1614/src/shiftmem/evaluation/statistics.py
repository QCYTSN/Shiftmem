"""Dependency-light paired statistical comparisons for formal experiments."""

from __future__ import annotations

from itertools import product
from math import erfc, exp, isfinite, lgamma, log, sqrt
from statistics import mean, median, stdev
from typing import Sequence


_T_975 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    11: 2.201,
    12: 2.179,
    13: 2.160,
    14: 2.145,
    15: 2.131,
    16: 2.120,
    17: 2.110,
    18: 2.101,
    19: 2.093,
    20: 2.086,
    21: 2.080,
    22: 2.074,
    23: 2.069,
    24: 2.064,
    25: 2.060,
    26: 2.056,
    27: 2.052,
    28: 2.048,
    29: 2.045,
    30: 2.042,
}


def _finite(values: Sequence[float]) -> list[float]:
    result = [float(value) for value in values]
    if not result or not all(isfinite(value) for value in result):
        raise ValueError("values must be non-empty and finite")
    return result


def paired_summary(pairs: Sequence[tuple[float, float]]) -> dict[str, float | int]:
    differences = _finite([left - right for left, right in pairs])
    n = len(differences)
    average = mean(differences)
    sd = stdev(differences) if n > 1 else 0.0
    critical = _T_975.get(n - 1, 1.96) if n > 1 else 0.0
    margin = critical * sd / sqrt(n) if n > 1 else 0.0
    effect = average / sd if sd else (0.0 if average == 0 else float("inf") * (1 if average > 0 else -1))
    return {
        "n": n,
        "mean_difference": average,
        "sd_difference": sd,
        "ci_low": average - margin,
        "ci_high": average + margin,
        "effect_size_dz": effect,
    }


def _betacf(a: float, b: float, x: float) -> float:
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    d = 1e-300 if abs(d) < 1e-300 else d
    d = 1.0 / d
    result = d
    for iteration in range(1, 201):
        m2 = 2 * iteration
        aa = iteration * (b - iteration) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1e-300 if abs(d) < 1e-300 else d
        c = 1.0 + aa / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1.0 / d
        result *= d * c
        aa = -(a + iteration) * (qab + iteration) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1e-300 if abs(d) < 1e-300 else d
        c = 1.0 + aa / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1.0 / d
        delta = d * c
        result *= delta
        if abs(delta - 1.0) < 3e-14:
            break
    return result


def _regularized_beta(x: float, a: float, b: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    front = exp(lgamma(a + b) - lgamma(a) - lgamma(b) + a * log(x) + b * log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1 - x) / b


def paired_t_test(differences: Sequence[float]) -> dict[str, float | str]:
    values = _finite(differences)
    if len(values) < 2:
        raise ValueError("paired t-test requires at least two differences")
    average = mean(values)
    sd = stdev(values)
    if sd == 0:
        statistic = 0.0 if average == 0 else float("inf") * (1 if average > 0 else -1)
        p_value = 1.0 if average == 0 else 0.0
    else:
        statistic = average / (sd / sqrt(len(values)))
        df = len(values) - 1
        x = df / (df + statistic * statistic)
        p_value = _regularized_beta(x, df / 2, 0.5)
    return {"method": "paired_t_test", "statistic": statistic, "p_value": p_value}


def _average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + 1 + end) / 2
        for index in order[start:end]:
            ranks[index] = rank
        start = end
    return ranks


def wilcoxon_signed_rank(differences: Sequence[float]) -> dict[str, float | str]:
    values = [value for value in _finite(differences) if value != 0]
    if not values:
        return {"method": "wilcoxon_signed_rank_exact", "statistic": 0.0, "p_value": 1.0}
    ranks = _average_ranks([abs(value) for value in values])
    positive = sum(rank for rank, value in zip(ranks, values) if value > 0)
    total = sum(ranks)
    statistic = min(positive, total - positive)
    if len(values) <= 20:
        extreme = 0
        for signs in product((0, 1), repeat=len(values)):
            candidate = sum(rank for rank, sign in zip(ranks, signs) if sign)
            if min(candidate, total - candidate) <= statistic + 1e-12:
                extreme += 1
        p_value = extreme / (2 ** len(values))
        method = "wilcoxon_signed_rank_exact"
    else:
        expected = total / 2
        variance = sum(rank * rank for rank in ranks) / 4
        z = (abs(positive - expected) - 0.5) / sqrt(variance)
        p_value = erfc(max(0.0, z) / sqrt(2))
        method = "wilcoxon_signed_rank_normal"
    return {"method": method, "statistic": statistic, "p_value": p_value}


def _normality_p_value(values: list[float]) -> float:
    if len(values) < 8:
        return 1.0
    average = mean(values)
    second = mean([(value - average) ** 2 for value in values])
    if second == 0:
        return 1.0
    skew = mean([(value - average) ** 3 for value in values]) / second ** 1.5
    kurtosis = mean([(value - average) ** 4 for value in values]) / second ** 2
    statistic = len(values) / 6 * (skew * skew + (kurtosis - 3) ** 2 / 4)
    return exp(-statistic / 2)


def _has_severe_outlier(values: list[float]) -> bool:
    center = median(values)
    deviations = [abs(value - center) for value in values]
    mad = median(deviations)
    if mad == 0:
        return any(deviation > 0 for deviation in deviations)
    return max(deviations) > 6 * mad


def paired_analysis(pairs: Sequence[tuple[float, float]]) -> dict[str, object]:
    differences = _finite([left - right for left, right in pairs])
    normality_p = _normality_p_value(differences)
    severe_outlier = _has_severe_outlier(differences)
    test = (
        wilcoxon_signed_rank(differences)
        if normality_p < 0.05 or severe_outlier
        else paired_t_test(differences)
    )
    return {
        **paired_summary(pairs),
        "normality_p_value": normality_p,
        "severe_outlier": severe_outlier,
        "test": test,
    }


def holm_adjust(p_values: Sequence[float]) -> list[float]:
    values = _finite(p_values)
    if any(value < 0 or value > 1 for value in values):
        raise ValueError("p-values must be in [0, 1]")
    order = sorted(range(len(values)), key=values.__getitem__)
    adjusted = [0.0] * len(values)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (len(values) - rank) * values[index])
        adjusted[index] = min(1.0, running)
    return adjusted
