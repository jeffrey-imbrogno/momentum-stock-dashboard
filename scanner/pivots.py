from __future__ import annotations

import math

import pandas as pd

from config import ScannerConfig
from scanner.indicators import add_indicators
from scanner.models import PivotResult, TrendTemplateResult, VCPResult


NO_VALID_SETUP = PivotResult(
    setup_type="NO VALID SETUP",
    pivot=None,
    entry=None,
    valid_setup=False,
    confidence=0,
    rationale=["No reliable base or pivot was detected."],
)


def _entry_from_pivot(pivot: float | None, config: ScannerConfig) -> float | None:
    if pivot is None or not math.isfinite(pivot) or pivot <= 0:
        return None
    return float(pivot * (1 + config.entry_buffer))


def calculate_entry(pivot: float, config: ScannerConfig) -> float:
    return float(pivot * (1 + config.entry_buffer))


def detect_pivot(
    price_history: pd.DataFrame,
    trend: TrendTemplateResult,
    vcp: VCPResult,
    config: ScannerConfig,
) -> PivotResult:
    if price_history is None or price_history.empty or len(price_history) < 80:
        return PivotResult(
            setup_type="INSUFFICIENT DATA",
            pivot=None,
            entry=None,
            valid_setup=False,
            confidence=0,
            rationale=["At least 80 trading sessions are needed for setup detection."],
        )

    df = add_indicators(price_history)
    last = df.iloc[-1]
    close = float(last["Close"])
    high_52 = float(df.tail(min(252, len(df)))["High"].max())
    candidates: list[PivotResult] = []

    recent_55 = df.tail(55)
    recent_45 = df.tail(45)
    recent_25 = df.tail(25)

    if vcp.score >= 55 and vcp.contraction_count >= 2 and trend.score >= 5:
        pivot = float(recent_55.iloc[:-1]["High"].max())
        base_depth = (pivot - float(recent_55["Low"].min())) / pivot if pivot > 0 else 1
        if pivot > 0 and base_depth <= 0.38 and close >= pivot * 0.82:
            confidence = min(95, int(42 + vcp.score * 0.45 + trend.score * 2))
            candidates.append(
                PivotResult(
                    setup_type="VCP PIVOT",
                    pivot=pivot,
                    entry=_entry_from_pivot(pivot, config),
                    valid_setup=True,
                    confidence=confidence,
                    rationale=[
                        "VCP quality is high enough to define final contraction resistance.",
                        f"Base depth is {base_depth * 100:.1f}%, within the model limit.",
                    ],
                )
            )

    flat_range = (float(recent_45["High"].max()) - float(recent_45["Low"].min())) / float(recent_45["High"].max())
    if flat_range <= 0.16 and close > float(last.get("SMA50", 0) or 0) and close >= high_52 * 0.78:
        pivot = float(recent_45.iloc[:-1]["High"].max())
        candidates.append(
            PivotResult(
                setup_type="FLAT BASE",
                pivot=pivot,
                entry=_entry_from_pivot(pivot, config),
                valid_setup=True,
                confidence=int(max(50, min(85, 82 - flat_range * 120))),
                rationale=[
                    "Recent range is tight enough for a flat-base candidate.",
                    "Price remains near its 52-week high and above the 50-day average.",
                ],
            )
        )

    if len(df) >= 150:
        cup_window = df.tail(150)
        cup_high = float(cup_window["High"].max())
        cup_low = float(cup_window["Low"].min())
        correction = (cup_high - cup_low) / cup_high if cup_high > 0 else 1
        handle_range = (float(recent_25["High"].max()) - float(recent_25["Low"].min())) / float(recent_25["High"].max())
        if 0.12 <= correction <= 0.40 and handle_range <= 0.15 and close >= cup_high * 0.82:
            pivot = float(recent_25.iloc[:-1]["High"].max())
            candidates.append(
                PivotResult(
                    setup_type="CUP WITH HANDLE",
                    pivot=pivot,
                    entry=_entry_from_pivot(pivot, config),
                    valid_setup=True,
                    confidence=int(max(48, min(82, 72 - handle_range * 80 + trend.score))),
                    rationale=[
                        f"Intermediate correction is {correction * 100:.1f}% with a controlled handle.",
                        "This is an approximate algorithmic cup-with-handle detection.",
                    ],
                )
            )

    if len(df) >= 90:
        run_window = df.tail(90).head(65)
        flag = df.tail(25)
        start = float(run_window["Close"].iloc[0])
        run_high = float(run_window["High"].max())
        flag_range = (float(flag["High"].max()) - float(flag["Low"].min())) / float(flag["High"].max())
        if start > 0 and run_high / start - 1 >= 0.75 and flag_range <= 0.25 and close >= run_high * 0.70:
            pivot = float(flag.iloc[:-1]["High"].max())
            candidates.append(
                PivotResult(
                    setup_type="HIGH TIGHT FLAG",
                    pivot=pivot,
                    entry=_entry_from_pivot(pivot, config),
                    valid_setup=True,
                    confidence=70,
                    rationale=[
                        "A large prior advance was followed by a relatively tight consolidation.",
                    ],
                )
            )

    ema21 = float(last["EMA21"]) if pd.notna(last["EMA21"]) else None
    sma50 = float(last["SMA50"]) if pd.notna(last["SMA50"]) else None
    if (
        trend.score >= 7
        and ema21
        and sma50
        and close > sma50
        and abs(close / ema21 - 1) <= 0.03
        and recent_25["Volume"].tail(5).mean() < recent_25["Volume"].head(20).mean() * 1.15
    ):
        pivot = float(recent_25.iloc[:-1]["High"].max())
        candidates.append(
            PivotResult(
                setup_type="21 EMA PULLBACK",
                pivot=pivot,
                entry=_entry_from_pivot(pivot, config),
                valid_setup=True,
                confidence=62,
                rationale=[
                    "Stage 2 trend is intact and price is consolidating near the 21-day EMA.",
                    "Recent pullback volume is controlled.",
                ],
            )
        )

    gap_candidates = []
    avg_volume = df["Volume"].rolling(20).mean()
    for index in range(max(1, len(df) - 45), len(df) - 5):
        previous_close = df["Close"].iloc[index - 1]
        open_price = df["Open"].iloc[index]
        if previous_close > 0 and open_price / previous_close - 1 >= 0.10:
            if df["Volume"].iloc[index] >= avg_volume.iloc[index] * 1.8:
                gap_candidates.append(index)
    if gap_candidates:
        gap_index = gap_candidates[-1]
        post_gap = df.iloc[gap_index:].tail(30)
        if len(post_gap) >= 8:
            pivot = float(post_gap.iloc[:-1]["High"].max())
            candidates.append(
                PivotResult(
                    setup_type="POST-EARNINGS BREAKOUT",
                    pivot=pivot,
                    entry=_entry_from_pivot(pivot, config),
                    valid_setup=True,
                    confidence=68,
                    rationale=[
                        "A recent high-volume gap created a post-earnings continuation setup candidate.",
                    ],
                )
            )

    valid_candidates = [candidate for candidate in candidates if candidate.pivot and candidate.entry]
    if not valid_candidates:
        return NO_VALID_SETUP

    valid_candidates.sort(key=lambda candidate: candidate.confidence, reverse=True)
    return valid_candidates[0]
