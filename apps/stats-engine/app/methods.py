"""Pure statistical methods.

All functions are deterministic. The service never fetches data and never
persists state; it receives a complete series and returns a complete result.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from statistics import median

import numpy as np
import pymannkendall as mk
import statsmodels.api as sm
from scipy import stats

from .config import DEFAULT_CONFIG, MethodConfig, METHOD_VERSION
from .models import BatchEntry, BatchResponse, BatchResultEntry, Diagnostics, TrendResult

VARIABLE_LABELS = {
    "T2M": "Air temperature at 2 m",
    "T2M_MIN": "Minimum temperature at 2 m",
    "T2M_MAX": "Maximum temperature at 2 m",
    "PRECTOTCORR": "Corrected precipitation",
    "GWETROOT": "Root-zone soil wetness",
    "GWETTOP": "Surface soil wetness",
    "RH2M": "Relative humidity at 2 m",
    "WS2M": "Wind speed at 2 m",
    "ALLSKY_SFC_SW_DWN": "All-sky shortwave radiation",
    "AOD_55": "Aerosol optical depth at 550 nm",
}

SEASON_MONTHS = {
    "all": tuple(range(1, 13)),
    "DJF": (12, 1, 2),
    "MAM": (3, 4, 5),
    "JJA": (6, 7, 8),
    "SON": (9, 10, 11),
}

SIGNIFICANCE_ALPHA = 0.05


@dataclass
class PreparedSeries:
    years: np.ndarray
    months: np.ndarray
    values: np.ndarray
    start: str | None
    end: str | None
    expected_n: int
    missing: int


def parse_ts(ts: str) -> tuple[int, int]:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        dt = datetime.fromisoformat(ts + "-01T00:00:00+00:00")
    return dt.year, dt.month


def _prepare(points, season: str, frequency: str) -> PreparedSeries:
    rows: list[tuple[int, int, float]] = []
    missing = 0
    for point in points:
        year, month = parse_ts(point.ts)
        if point.value is None or not math.isfinite(float(point.value)):
            missing += 1
            continue
        rows.append((year, month, float(point.value)))

    if frequency == "annual":
        annual: dict[int, list[float]] = {}
        for year, month, value in rows:
            annual.setdefault(year, []).append(value)
        rows = [(year, 1, float(np.mean(vals))) for year, vals in sorted(annual.items()) if len(vals) >= 10]
        expected_n = max(1, len(range(min(annual), max(annual) + 1))) if annual else 0
        start = f"{min(annual)}-01-01T00:00:00Z" if annual else None
        end = f"{max(annual)}-01-01T00:00:00Z" if annual else None
    else:
        months = SEASON_MONTHS[season]
        rows = [row for row in rows if row[1] in months]
        years = sorted({row[0] for row in rows})
        expected_n = len(years) * len(months) if years else 0
        start = f"{years[0]}-01-01T00:00:00Z" if years else None
        end = f"{years[-1]}-12-01T00:00:00Z" if years else None

    years = np.array([row[0] for row in rows], dtype=float)
    months = np.array([row[1] for row in rows], dtype=int)
    values = np.array([row[2] for row in rows], dtype=float)
    return PreparedSeries(years, months, values, start, end, expected_n, missing)


def _deseasonalize(years: np.ndarray, months: np.ndarray, values: np.ndarray) -> np.ndarray:
    anomalies = values.astype(float).copy()
    for month in np.unique(months):
        mask = months == month
        if mask.sum() >= 2:
            anomalies[mask] -= values[mask].mean()
    return anomalies


def _seasonal_sen(years: np.ndarray, months: np.ndarray, values: np.ndarray) -> float | None:
    monthly_slopes: list[float] = []
    for month in np.unique(months):
        mask = months == month
        ys = years[mask]
        vs = values[mask]
        slopes = [
            (vs[j] - vs[i]) / (ys[j] - ys[i])
            for i in range(len(vs))
            for j in range(i + 1, len(vs))
            if ys[j] != ys[i]
        ]
        if slopes:
            monthly_slopes.append(float(median(slopes)))
    return float(median(monthly_slopes)) * 10.0 if monthly_slopes else None


def _olS_hac(years: np.ndarray, values: np.ndarray, lags: int) -> tuple[float, float, list[float]] | None:
    if len(values) < 4:
        return None
    x = sm.add_constant(years.astype(float))
    model = sm.OLS(values.astype(float), x).fit(
        cov_type="HAC", cov_kwds={"maxlags": max(1, lags)}, use_t=True
    )
    slope = float(model.params[1]) * 10.0
    p_value = float(model.pvalues[1])
    ci = model.conf_int(alpha=0.05)
    return slope, p_value, [float(ci[1][0]) * 10.0, float(ci[1][1]) * 10.0]


def _mk_test(values: np.ndarray, autocorrelation: str, seasonal_period: int | None):
    clean = values[np.isfinite(values)]
    if len(clean) < 10:
        return None
    try:
        if autocorrelation == "hamed_rao":
            result = mk.hamed_rao_modification_test(clean)
        elif seasonal_period:
            result = mk.seasonal_test(clean, period=seasonal_period)
        else:
            result = mk.original_test(clean)
    except Exception:
        result = None
    # The Hamed-Rao variance correction can go negative for strongly
    # autocorrelated series, which makes p undefined (NaN). Fall back to the
    # uncorrected test so a status=ok result always carries a usable p-value.
    if result is None or not np.isfinite(result.p):
        try:
            return mk.original_test(clean)
        except Exception:
            return None
    return result


def _completeness(n: int, expected: int) -> float:
    return float(n / expected) if expected else 0.0


def _format_p(p: float | None) -> str:
    if p is None:
        return "p unavailable"
    if p < 0.001:
        return "p < 0.001"
    return f"p = {p:.3f}"


def analyze_points(
    points,
    *,
    variable_key: str = "T2M",
    units: str = "",
    frequency: str = "monthly",
    options=None,
    config: MethodConfig = DEFAULT_CONFIG,
) -> TrendResult:
    options = options or type("Options", (), {
        "season": "all", "seasonal": "deseasonalize", "autocorrelation": "hamed_rao",
        "confidence": 0.95, "min_years": 10, "test": "mann_kendall",
    })()
    prepared = _prepare(points, options.season, frequency)
    n = len(prepared.values)
    completeness = _completeness(n, prepared.expected_n)
    min_years = config.min_years_annual if frequency == "annual" else options.min_years
    n_years = len(np.unique(prepared.years)) if n else 0
    label = VARIABLE_LABELS.get(variable_key, variable_key)
    unit_text = f" {units}" if units else ""

    base = TrendResult(
        method_version=METHOD_VERSION,
        n=n,
        expected_n=prepared.expected_n,
        completeness=round(completeness, 4),
        start=prepared.start,
        end=prepared.end,
        test="hamed_rao_mann_kendall" if options.autocorrelation == "hamed_rao" else "mann_kendall",
    )

    if n_years < min_years or completeness < config.min_completeness:
        base.status = "insufficient_data"
        base.verdict = (
            f"There are only {n_years} years of usable data for {label.lower()}. "
            f"A trend test needs at least {min_years} years."
        )
        base.caveats = ["Increase the period or choose a variable with longer coverage."]
        base.diagnostics = Diagnostics(missing=prepared.missing, min_n_met=False)
        return base

    if frequency == "annual":
        test_values = prepared.values
        adjusted = False
    elif options.seasonal == "raw":
        test_values = prepared.values
        adjusted = False
    else:
        test_values = _deseasonalize(prepared.years, prepared.months, prepared.values)
        adjusted = True

    sen_slope = _seasonal_sen(prepared.years, prepared.months, prepared.values)
    if sen_slope is None and len(test_values) >= 2:
        sen_slope = float(stats.theilslopes(test_values, prepared.years)[0]) * 10.0

    mk_result = _mk_test(
        test_values,
        options.autocorrelation,
        12 if (frequency == "monthly" and options.season == "all" and options.seasonal != "raw") else None,
    )
    p_value = float(mk_result.p) if mk_result is not None else None
    ols = _olS_hac(prepared.years, test_values, config.hac_lags) if len(test_values) >= 10 else None
    p_ols = ols[1] if ols else None

    if sen_slope is not None:
        try:
            low, high = stats.theilslopes(test_values, prepared.years)[2:4]
            ci = [float(low) * 10.0, float(high) * 10.0]
        except Exception:
            ci = None
    else:
        ci = None
    if ols is not None and ci is None:
        ci = ols[2]

    sig_mk = p_value is not None and p_value < SIGNIFICANCE_ALPHA
    sig_ols = p_ols is not None and p_ols < SIGNIFICANCE_ALPHA
    method_dependent = (p_value is not None and p_ols is not None and sig_mk != sig_ols)
    significant = bool(sig_mk and sig_ols) if options.test == "mann_kendall" else bool(sig_ols)

    direction = "none"
    if sen_slope is not None and significant:
        direction = "increasing" if sen_slope > 0 else "decreasing"

    caveats: list[str] = []
    if options.autocorrelation == "hamed_rao":
        caveats.append("Monthly values are autocorrelated; the Hamed-Rao correction is applied.")
    if adjusted:
        caveats.append("The seasonal cycle was removed before the trend test.")
    if completeness < config.good_completeness:
        caveats.append(f"Only {completeness:.0%} of the expected months are present.")
    if n_years < 15:
        caveats.append(f"Short record: {n_years} years. Treat the verdict as provisional.")
    caveats.append("A trend is a statistical association, not a causal attribution.")
    caveats.append("This is a MERRA-2 grid cell, not a weather station.")
    if method_dependent:
        caveats.append("The seasonal Mann-Kendall and OLS-HAC tests disagree; treat the verdict as method-dependent.")

    if method_dependent:
        conservative_p = max(p for p in (p_value, p_ols) if p is not None)
        base.verdict = (
            f"{label} changed by about {abs(sen_slope or 0):.3f}{unit_text} per decade, "
            f"but the verdict is method-dependent: Seasonal Mann-Kendall {_format_p(p_value)} "
            f"versus OLS HAC {_format_p(p_ols)}. Do not overclaim this trend."
        )
    elif significant:
        direction_word = "increased" if (sen_slope or 0) > 0 else "decreased"
        base.verdict = (
            f"{label} {direction_word} by about {abs(sen_slope or 0):.3f}{unit_text} per decade. "
            f"The trend is statistically significant ({_format_p(p_value)}, n = {n}). "
            "This is a statistical association, not a causal attribution."
        )
    else:
        base.verdict = (
            f"No significant trend in {label.lower()} in this window "
            f"({_format_p(p_value)}, n = {n}). This is not the same as no change."
        )

    base.slope_per_decade = round(sen_slope, 4) if sen_slope is not None else None
    base.sen_slope_per_decade = base.slope_per_decade
    base.slope_ci95 = [round(ci[0], 4), round(ci[1], 4)] if ci else None
    base.p_value = round(p_value, 6) if p_value is not None else None
    base.p_value_ols = round(p_ols, 6) if p_ols is not None else None
    base.ols_slope_per_decade = round(ols[0], 4) if ols else None
    base.significant = significant
    base.method_dependent = method_dependent
    base.direction = direction
    base.caveats = caveats
    base.diagnostics = Diagnostics(
        missing=prepared.missing,
        seasonal_adjusted=adjusted,
        min_n_met=True,
    )
    return base


def batch_fdr(entries: list[BatchEntry]) -> BatchResponse:
    from statsmodels.stats.multitest import multipletests

    results: list[TrendResult] = []
    for entry in entries:
        result = analyze_points(
            entry.points,
            variable_key=entry.variable_key,
            units=entry.units,
            frequency=entry.frequency,
            options=entry.options,
        )
        result.series_id = entry.series_id
        results.append(result)
    p_values = [r.p_value if r.status == "ok" and r.p_value is not None else 1.0 for r in results]
    adjusted = multipletests(p_values, alpha=0.05, method="fdr_bh")[1]
    output: list[BatchResultEntry] = []
    for result, q in zip(results, adjusted):
        output.append(
            BatchResultEntry(
                series_id=result.series_id or "",
                status=result.status,
                p_value=result.p_value,
                p_adj=float(q),
                significant=result.significant,
                significant_fdr=bool(result.status == "ok" and q < 0.05 and result.significant),
                verdict=result.verdict,
            )
        )
    return BatchResponse(method_version=METHOD_VERSION, results=output)


def evidence_level(q: float | None, n_years: int, method_dependent: bool = False) -> str:
    if n_years < 10 or q is None:
        return "insufficient"
    if q < 0.01 and n_years >= 20 and not method_dependent:
        return "strong"
    if q < 0.05 and not method_dependent:
        return "moderate"
    if q < 0.01 and method_dependent:
        return "moderate"
    return "weak"


def standardized_slope(slope_per_decade: float | None, annual_values: list[float]) -> float | None:
    if slope_per_decade is None or len(annual_values) < 5:
        return None
    arr = np.array(annual_values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) < 5:
        return None
    x = np.arange(len(arr), dtype=float)
    slope, intercept = np.polyfit(x, arr, 1)
    detrended = arr - (slope * x + intercept)
    mad = float(np.median(np.abs(detrended - np.median(detrended))))
    scale = 1.4826 * mad
    if scale <= 0:
        return None
    return float(slope_per_decade / (scale * 10.0))
