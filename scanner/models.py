from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd


@dataclass(slots=True)
class TrendTemplateResult:
    score: int
    total: int
    conditions: dict[str, bool]
    insufficient_data: bool = False

    @property
    def label(self) -> str:
        return f"{self.score}/{self.total}"

    @property
    def critical_failure(self) -> bool:
        critical = [
            "price_above_150_sma",
            "price_above_200_sma",
            "sma_50_above_150",
            "sma_150_above_200",
        ]
        return any(not self.conditions.get(key, False) for key in critical)


@dataclass(slots=True)
class VCPResult:
    score: int
    contractions: list[float]
    contraction_count: int
    atr_compression: bool
    range_compression: bool
    volume_dry_up: bool
    declining_selling_volume: bool
    tight_closes: bool
    price_near_highs: bool
    tightening_near_emas: bool
    volume_score: int
    notes: list[str] = field(default_factory=list)

    @property
    def sequence_label(self) -> str:
        if not self.contractions:
            return "N/A"
        return " -> ".join(f"{value:.1f}%" for value in self.contractions)


@dataclass(slots=True)
class PivotResult:
    setup_type: str
    pivot: float | None
    entry: float | None
    valid_setup: bool
    confidence: int
    rationale: list[str] = field(default_factory=list)


@dataclass(slots=True)
class StopPlan:
    stop: float | None
    risk_per_share: float | None
    stop_pct: float | None
    target_2r: float | None
    target_3r: float | None
    shares: int
    position_value: float | None
    dollar_risk: float
    candidates: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class FundamentalSnapshot:
    revenue_growth: float | None = None
    earnings_growth: float | None = None
    profit_margin: float | None = None
    market_cap: float | None = None
    forward_pe: float | None = None
    earnings_date: datetime | None = None
    days_to_earnings: int | None = None
    sector: str | None = None
    industry: str | None = None
    score: int = 55


@dataclass(slots=True)
class MarketRegime:
    score: int
    classification: str
    exposure: str
    index_details: dict[str, dict[str, Any]]
    breadth: dict[str, float]


@dataclass(slots=True)
class StockAnalysis:
    ticker: str
    company: str
    exchange: str
    sector: str
    industry: str
    status: str
    current_price: float | None
    score: int
    score_breakdown: dict[str, float]
    trend_template: TrendTemplateResult
    momentum_rs: int
    vcp: VCPResult
    pivot: PivotResult
    stop_plan: StopPlan
    fundamentals: FundamentalSnapshot
    distance_from_entry_pct: float | None
    avg_dollar_volume: float | None
    atr: float | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    history: pd.DataFrame | None = None


@dataclass(slots=True)
class ScanResult:
    analyses: list[StockAnalysis]
    market: MarketRegime
    diagnostics: list[str]
    scanned_at: datetime
