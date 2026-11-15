"""Single source of truth for thresholds and the method version."""

from __future__ import annotations

from dataclasses import dataclass, field


METHOD_VERSION = "1.0.0"
NORMALIZATION_VERSION = "1.0.0"


@dataclass(frozen=True)
class MethodConfig:
    min_years_monthly: int = 10
    min_years_annual: int = 15
    min_completeness: float = 0.70
    good_completeness: float = 0.90
    confidence: float = 0.95
    hac_lags: int = 12
    fdr_alpha: float = 0.05

    evidence_strong_q: float = 0.01
    evidence_moderate_q: float = 0.05
    evidence_strong_years: int = 20

    caveats: tuple[str, ...] = field(
        default=(
            "A trend is a statistical association, not a causal attribution.",
            "NASA POWER values describe a MERRA-2 grid cell, not a weather station.",
        )
    )


DEFAULT_CONFIG = MethodConfig()
