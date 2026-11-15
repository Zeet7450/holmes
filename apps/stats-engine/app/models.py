"""Typed HTTP contract for the stats service."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


Seasonal = Literal["raw", "deseasonalize", "annual"]
Season = Literal["all", "DJF", "MAM", "JJA", "SON"]
TestName = Literal["mann_kendall", "ols"]
Autocorrelation = Literal["none", "hamed_rao"]


class SeriesPoint(BaseModel):
    ts: str
    value: float | None = None


class AnalysisOptions(BaseModel):
    seasonal: Seasonal = "deseasonalize"
    test: TestName = "mann_kendall"
    autocorrelation: Autocorrelation = "hamed_rao"
    confidence: float = 0.95
    min_years: int = 10
    season: Season = "all"


class AnalyzeRequest(BaseModel):
    series_id: str
    variable_key: str
    units: str
    frequency: Literal["monthly", "annual"] = "monthly"
    aggregation: Literal["mean", "sum"] = "mean"
    points: list[SeriesPoint] = Field(min_length=1)
    options: AnalysisOptions = Field(default_factory=AnalysisOptions)

    @field_validator("points")
    @classmethod
    def points_are_ordered(cls, points: list[SeriesPoint]) -> list[SeriesPoint]:
        return sorted(points, key=lambda p: p.ts)


class Diagnostics(BaseModel):
    missing: int = 0
    provisional: int = 0
    seasonal_adjusted: bool = False
    min_n_met: bool = True
    rejected_out_of_range: int = 0


class TrendResult(BaseModel):
    method_version: str
    series_id: str | None = None
    status: Literal["ok", "insufficient_data"] = "ok"
    n: int = 0
    expected_n: int = 0
    completeness: float = 0.0
    start: str | None = None
    end: str | None = None
    slope_per_decade: float | None = None
    slope_ci95: list[float] | None = None
    sen_slope_per_decade: float | None = None
    p_value: float | None = None
    p_value_ols: float | None = None
    ols_slope_per_decade: float | None = None
    test: str | None = None
    significant: bool = False
    method_dependent: bool = False
    direction: Literal["increasing", "decreasing", "none"] = "none"
    verdict: str = ""
    caveats: list[str] = Field(default_factory=list)
    diagnostics: Diagnostics = Field(default_factory=Diagnostics)


class BatchEntry(BaseModel):
    series_id: str
    variable_key: str
    units: str
    frequency: Literal["monthly", "annual"] = "monthly"
    aggregation: Literal["mean", "sum"] = "mean"
    points: list[SeriesPoint]
    options: AnalysisOptions = Field(default_factory=AnalysisOptions)


class FdrOptions(BaseModel):
    alpha: float = 0.05
    method: Literal["fdr_bh"] = "fdr_bh"


class BatchRequest(BaseModel):
    series: list[BatchEntry] = Field(min_length=1, max_length=500)
    fdr: FdrOptions = Field(default_factory=FdrOptions)


class BatchResultEntry(BaseModel):
    series_id: str
    status: Literal["ok", "insufficient_data"]
    p_value: float | None = None
    p_adj: float | None = None
    significant: bool = False
    significant_fdr: bool = False
    verdict: str = ""


class BatchResponse(BaseModel):
    method_version: str
    results: list[BatchResultEntry]
