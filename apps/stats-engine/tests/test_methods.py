"""Statistical behaviour tests for the pure methods."""

from __future__ import annotations

import numpy as np
import pytest

from app.methods import analyze_points, batch_fdr
from app.models import BatchEntry, SeriesPoint


def monthly_points(years: int, value_fn, *, seed: int = 0, start_year: int = 2000) -> list[SeriesPoint]:
    rng = np.random.default_rng(seed)
    return [
        SeriesPoint(
            ts=f"{start_year + year}-{month:02d}",
            value=float(value_fn(year, month, rng)),
        )
        for year in range(years)
        for month in range(1, 13)
    ]


def test_increasing_series_is_positive_and_significant():
    points = monthly_points(20, lambda y, m, rng: 0.5 * y + rng.normal(0, 0.1), seed=1)
    result = analyze_points(points, variable_key="T2M", units="°C")

    assert result.status == "ok"
    assert result.n == 240
    assert result.expected_n == 240
    assert result.completeness == pytest.approx(1.0)
    assert result.slope_per_decade == pytest.approx(5.0, abs=0.5)
    assert result.sen_slope_per_decade == pytest.approx(5.0, abs=0.5)
    assert result.p_value is not None and result.p_value < 0.05
    assert result.significant is True
    assert result.direction == "increasing"
    assert result.test == "hamed_rao_mann_kendall"


def test_decreasing_series_is_negative_and_significant():
    points = monthly_points(20, lambda y, m, rng: -0.4 * y + rng.normal(0, 0.1), seed=2)
    result = analyze_points(points, variable_key="T2M", units="°C")

    assert result.status == "ok"
    assert result.slope_per_decade == pytest.approx(-4.0, abs=0.5)
    assert result.p_value is not None and result.p_value < 0.05
    assert result.significant is True
    assert result.direction == "decreasing"


def test_white_noise_is_rarely_significant():
    significant = 0
    trials = 40
    for seed in range(trials):
        points = monthly_points(20, lambda y, m, rng: rng.normal(0, 1), seed=1000 + seed)
        if analyze_points(points, variable_key="T2M").significant:
            significant += 1

    # Each test has a 5% false-positive rate; allow a generous margin so the
    # test fails only on systematic over-detection, not on one noisy seed.
    assert significant <= 8, f"{significant}/{trials} white-noise series were significant"


def test_seasonal_cycle_without_trend_is_not_significant_after_deseasonalizing():
    results = [
        analyze_points(
            monthly_points(
                20,
                lambda y, m, rng: 5.0 * np.sin(2 * np.pi * (m - 1) / 12) + rng.normal(0, 0.5),
                seed=200 + seed,
            ),
            variable_key="T2M",
        )
        for seed in range(5)
    ]

    assert all(result.status == "ok" for result in results)
    assert all(result.diagnostics.seasonal_adjusted for result in results)
    # A 5% false-positive rate is expected per series; allow one outlier.
    assert sum(result.significant for result in results) <= 1
    for result in results:
        assert result.p_value is not None
        if not result.significant:
            assert result.p_value > 0.05


def test_short_series_returns_insufficient_data():
    points = monthly_points(5, lambda y, m, rng: 0.5 * y, seed=3)
    result = analyze_points(points, variable_key="T2M", units="°C")

    assert result.status == "insufficient_data"
    assert result.n == 60
    assert result.completeness == pytest.approx(1.0)
    assert "5 years" in result.verdict
    assert "at least 10 years" in result.verdict
    assert result.diagnostics.min_n_met is False
    assert result.significant is False
    assert result.slope_per_decade is None


def test_missing_months_are_reflected_in_completeness():
    all_points = monthly_points(20, lambda y, m, rng: 0.3 * y + rng.normal(0, 0.1), seed=4)
    points = [point for point in all_points if int(point.ts.split("-")[1]) not in (7, 8)]
    result = analyze_points(points, variable_key="T2M")

    assert result.status == "ok"
    assert result.n == 200
    assert result.expected_n == 240
    assert result.completeness == pytest.approx(200 / 240, abs=1e-4)
    assert any("expected months" in caveat for caveat in result.caveats)

    incomplete = [point for point in all_points if int(point.ts.split("-")[1]) > 8]
    below_threshold = analyze_points(incomplete, variable_key="T2M")
    assert below_threshold.status == "insufficient_data"
    assert below_threshold.completeness == pytest.approx(4 / 12, abs=1e-4)


def test_missing_values_are_counted_and_skipped():
    points = monthly_points(20, lambda y, m, rng: 0.3 * y + rng.normal(0, 0.1), seed=6)
    points[::20] = [SeriesPoint(ts=point.ts, value=None) for point in points[::20]]
    result = analyze_points(points, variable_key="T2M")

    assert result.status == "ok"
    assert result.n == 228
    assert result.diagnostics.missing == 12
    assert result.completeness == pytest.approx(228 / 240, abs=1e-4)


def test_batch_fdr_is_monotonic_and_bounded():
    entries = [
        BatchEntry(
            series_id="strong-increase",
            variable_key="T2M",
            units="°C",
            points=monthly_points(20, lambda y, m, rng: 0.5 * y + rng.normal(0, 0.1), seed=11),
        ),
        BatchEntry(
            series_id="weak-increase",
            variable_key="T2M",
            units="°C",
            points=monthly_points(20, lambda y, m, rng: 0.05 * y + rng.normal(0, 0.5), seed=12),
        ),
        BatchEntry(
            series_id="decrease",
            variable_key="T2M",
            units="°C",
            points=monthly_points(20, lambda y, m, rng: -0.4 * y + rng.normal(0, 0.1), seed=13),
        ),
        BatchEntry(
            series_id="flat",
            variable_key="T2M",
            units="°C",
            points=monthly_points(20, lambda y, m, rng: rng.normal(0, 1), seed=14),
        ),
        BatchEntry(
            series_id="short",
            variable_key="T2M",
            units="°C",
            points=monthly_points(5, lambda y, m, rng: 0.5 * y, seed=15),
        ),
    ]

    response = batch_fdr(entries)
    assert [row.series_id for row in response.results] == [entry.series_id for entry in entries]

    for row in response.results:
        assert row.p_adj is not None
        assert 0.0 <= row.p_adj <= 1.0
        if row.p_value is not None:
            assert row.p_adj >= row.p_value - 1e-12
        if row.significant_fdr:
            assert row.p_adj < 0.05 and row.significant

    tested = sorted(
        (row.p_value, row.p_adj)
        for row in response.results
        if row.p_value is not None and row.status == "ok"
    )
    assert [q for _, q in tested] == sorted(q for _, q in tested)
    assert response.results[0].significant_fdr is True
    assert response.results[-1].status == "insufficient_data"
    assert response.results[-1].p_value is None
    assert response.results[-1].significant_fdr is False
