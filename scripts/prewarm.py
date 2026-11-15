"""Precompute city trend statistics from cached NASA POWER monthly series.

Outputs (public + convex copies):
  apps/web/public/data/series.json
  apps/web/public/data/city-trends.json

The UI filters these precomputed results instantly. Historical data is
immutable, so this is a build-time step, not a runtime dependency.
"""

from __future__ import annotations

import json
import math
import multiprocessing as mp
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/stats-engine"))

from app.methods import analyze_points, evidence_level, standardized_slope  # noqa: E402
from app.config import METHOD_VERSION  # noqa: E402
from statsmodels.stats.multitest import multipletests  # noqa: E402

CITIES = json.loads((ROOT / "data/seed/cities.json").read_text())
VARIABLES = json.loads((ROOT / "data/seed/variables.json").read_text())
VARIABLE_BY_KEY = {v["key"]: v for v in VARIABLES}
RAW = ROOT / "data/seed/raw/power"

START_YEAR = 1981
END_YEAR = 2025
WINDOWS = [
    {"id": "full", "start": 1981, "end": 2025, "label": "FULL 1981–2025", "short": "FULL"},
    {"id": "35y", "start": 1991, "end": 2025, "label": "35Y 1991–2025", "short": "35Y"},
    {"id": "25y", "start": 2001, "end": 2025, "label": "25Y 2001–2025", "short": "25Y"},
    {"id": "15y", "start": 2011, "end": 2025, "label": "15Y 2011–2025", "short": "15Y"},
]
SEASONS = ["all", "DJF", "MAM", "JJA", "SON"]
SEASON_MONTHS = {
    "all": list(range(1, 13)),
    "DJF": [12, 1, 2],
    "MAM": [3, 4, 5],
    "JJA": [6, 7, 8],
    "SON": [9, 10, 11],
}


class Point:
    __slots__ = ("ts", "value")

    def __init__(self, ts: str, value: float | None):
        self.ts = ts
        self.value = value


def month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def finite(value):
    if value is None:
        return None
    try:
        return round(float(value), 6) if math.isfinite(float(value)) else None
    except (TypeError, ValueError):
        return None


def load_city(city_id: str) -> dict[str, list[tuple[int, int, float | None]]]:
    raw = json.loads((RAW / f"{city_id}.json").read_text())
    params = raw["properties"]["parameter"]
    out: dict[str, list[tuple[int, int, float | None]]] = {}
    for variable in VARIABLE_BY_KEY:
        values = params.get(variable, {})
        series: list[tuple[int, int, float | None]] = []
        for year in range(START_YEAR, END_YEAR + 1):
            for month in range(1, 13):
                key = f"{year:04d}{month:02d}"
                value = values.get(key)
                if value is None or value == -999 or value == -999.0:
                    value = None
                series.append((year, month, value))
        out[variable] = series
    return out


def annual_values(series, start: int, season: str) -> list[float]:
    months = SEASON_MONTHS[season]
    grouped: dict[int, list[float]] = {}
    for year, month, value in series:
        if year < start or month not in months or value is None:
            continue
        grouped.setdefault(year, []).append(value)
    minimum = 10 if season == "all" else max(2, len(months) - 1)
    return [sum(vals) / len(vals) for _, vals in sorted(grouped.items()) if len(vals) >= minimum]


def compute_city(city: dict) -> dict:
    series = load_city(city["id"])
    records: dict[str, dict[str, dict]] = {}
    compact: dict[str, list[float | None]] = {}

    for variable, rows in series.items():
        compact[variable] = [round(v, 3) if v is not None else None for _, _, v in rows]
        meta = VARIABLE_BY_KEY[variable]
        per_variable: dict[str, dict] = {}
        for window in WINDOWS:
            points = [
                Point(f"{year:04d}-{month:02d}-01T00:00:00Z", value)
                for year, month, value in rows
                if year >= window["start"]
            ]
            for season in SEASONS:
                options = SimpleNamespace(
                    season=season,
                    seasonal="deseasonalize",
                    autocorrelation="hamed_rao",
                    confidence=0.95,
                    min_years=10,
                    test="mann_kendall",
                )
                result = analyze_points(
                    points,
                    variable_key=variable,
                    units=meta["units"],
                    frequency="monthly",
                    options=options,
                )
                years = sorted({year for year, month, value in rows if year >= window["start"] and value is not None})
                effective_start = years[0] if years else window["start"]
                annual = annual_values(rows, window["start"], season)
                z = standardized_slope(result.slope_per_decade, annual)
                key = f"{window['id']}|{season}"
                per_variable[key] = {
                    "status": result.status,
                    "slope": finite(result.slope_per_decade),
                    "ci": [finite(result.slope_ci95[0]), finite(result.slope_ci95[1])]
                    if result.slope_ci95 else None,
                    "p": finite(result.p_value),
                    "pOls": finite(result.p_value_ols),
                    "olsSlope": finite(result.ols_slope_per_decade),
                    "significant": bool(result.significant),
                    "methodDependent": bool(result.method_dependent),
                    "direction": result.direction,
                    "n": int(result.n),
                    "nYears": len(years),
                    "coverage": finite(result.completeness),
                    "z": finite(z),
                    "effectiveStart": effective_start,
                }
        records[variable] = per_variable
    return {"id": city["id"], "records": records, "series": compact}


def attach_fdr(all_records: dict[str, dict]) -> None:
    # FDR across cities for each variable/window/season.
    for variable in VARIABLE_BY_KEY:
        for window in WINDOWS:
            for season in SEASONS:
                key = f"{window['id']}|{season}"
                entries = []
                for city_id, payload in all_records.items():
                    rec = payload["records"][variable][key]
                    entries.append((city_id, rec))
                pvals = [
                    rec["p"] if rec["status"] == "ok" and rec["p"] is not None and math.isfinite(rec["p"]) else 1.0
                    for _, rec in entries
                ]
                adjusted = multipletests(pvals, alpha=0.05, method="fdr_bh")[1]
                for (city_id, rec), q in zip(entries, adjusted):
                    qv = float(q) if math.isfinite(float(q)) else 1.0
                    rec["q"] = round(qv, 6)
                    rec["significantFdr"] = bool(rec["status"] == "ok" and qv < 0.05)
                    rec["evidence"] = evidence_level(
                        qv, rec["nYears"], rec["methodDependent"]
                    )

    # FDR across variables for each city/window/season (city notes).
    for city_id, payload in all_records.items():
        for window in WINDOWS:
            for season in SEASONS:
                key = f"{window['id']}|{season}"
                entries = [
                    (variable, payload["records"][variable][key])
                    for variable in VARIABLE_BY_KEY
                ]
                pvals = [
                    rec["p"] if rec["status"] == "ok" and rec["p"] is not None and math.isfinite(rec["p"]) else 1.0
                    for _, rec in entries
                ]
                adjusted = multipletests(pvals, alpha=0.05, method="fdr_bh")[1]
                for (variable, rec), q in zip(entries, adjusted):
                    qv = float(q) if math.isfinite(float(q)) else 1.0
                    rec["qVar"] = round(qv, 6)
                    rec["significantVar"] = bool(rec["status"] == "ok" and qv < 0.05)
                    rec["evidenceVar"] = evidence_level(
                        qv, rec["nYears"], rec["methodDependent"]
                    )


def main() -> int:
    started = datetime.now(timezone.utc)
    workers = max(2, min(8, os.cpu_count() or 2))
    print(f"Computing trends for {len(CITIES)} cities with {workers} workers…", flush=True)

    all_records: dict[str, dict] = {}
    with mp.Pool(workers) as pool:
        for index, payload in enumerate(pool.imap_unordered(compute_city, CITIES), start=1):
            all_records[payload["id"]] = {
                "records": payload["records"],
                "series": payload["series"],
            }
            if index % 10 == 0 or index == len(CITIES):
                print(f"  {index}/{len(CITIES)} cities", flush=True)

    print("Applying FDR corrections…", flush=True)
    attach_fdr(all_records)

    series_out = {city_id: payload["series"] for city_id, payload in all_records.items()}
    trends_out = {
        city_id: payload["records"] for city_id, payload in all_records.items()
    }

    out_dirs = [ROOT / "apps/web/public/data", ROOT / "convex/data", ROOT / "data/seed/out"]
    for out_dir in out_dirs:
        out_dir.mkdir(parents=True, exist_ok=True)

    series_payload = {
        "startYear": START_YEAR,
        "months": (END_YEAR - START_YEAR + 1) * 12,
        "cities": series_out,
    }
    trends_payload = {
        "methodVersion": METHOD_VERSION,
        "generatedAt": started.isoformat(),
        "windows": WINDOWS,
        "seasons": SEASONS,
        "cities": trends_out,
    }

    for out_dir in out_dirs:
        (out_dir / "series.json").write_text(json.dumps(series_payload, separators=(",", ":"), allow_nan=False))
        (out_dir / "city-trends.json").write_text(json.dumps(trends_payload, separators=(",", ":"), allow_nan=False))

    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    size = (ROOT / "apps/web/public/data/city-trends.json").stat().st_size / 1e6
    print(f"Done in {elapsed:.1f}s · trends {size:.2f} MB · method {METHOD_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
