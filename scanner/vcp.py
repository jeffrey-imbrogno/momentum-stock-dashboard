from __future__ import annotations

import pandas as pd

from scanner.indicators import add_indicators
from scanner.models import VCPResult


def _segment_contraction(segment: pd.DataFrame) -> float | None:
    if segment.empty:
        return None
    high = segment["High"].max()
    low = segment["Low"].min()
    if high <= 0:
        return None
    return float((high - low) / high * 100)


def detect_contractions(price_history: pd.DataFrame, lookback: int = 90) -> list[float]:
    if price_history is None or price_history.empty or len(price_history) < 45:
        return []
    recent = price_history.tail(min(lookback, len(price_history))).copy()
    parts = []
    step = max(15, len(recent) // 3)
    for start in range(0, len(recent), step):
        part = recent.iloc[start : start + step]
        value = _segment_contraction(part)
        if value is not None:
            parts.append(value)
        if len(parts) == 3:
            break
    return parts


def analyze_vcp(price_history: pd.DataFrame) -> VCPResult:
    if price_history is None or price_history.empty or len(price_history) < 60:
        return VCPResult(
            score=0,
            contractions=[],
            contraction_count=0,
            atr_compression=False,
            range_compression=False,
            volume_dry_up=False,
            declining_selling_volume=False,
            tight_closes=False,
            price_near_highs=False,
            tightening_near_emas=False,
            volume_score=0,
            notes=["Insufficient history for VCP analysis."],
        )

    df = add_indicators(price_history)
    contractions = detect_contractions(df)
    decreasing_sequence = len(contractions) >= 2 and all(
        contractions[i] > contractions[i + 1] * 1.03 for i in range(len(contractions) - 1)
    )

    last_10 = df.tail(10)
    last_20 = df.tail(20)
    prior_40 = df.tail(60).head(40)
    last_50 = df.tail(50)

    atr_now = df["ATR14"].iloc[-1]
    atr_median = df["ATR14"].tail(70).median()
    atr_compression = bool(pd.notna(atr_now) and pd.notna(atr_median) and atr_now < atr_median * 0.85)

    daily_range_pct = ((last_10["High"] - last_10["Low"]) / last_10["Close"]).mean()
    prior_range_pct = ((last_50["High"] - last_50["Low"]) / last_50["Close"]).mean()
    range_compression = bool(pd.notna(daily_range_pct) and pd.notna(prior_range_pct) and daily_range_pct < prior_range_pct * 0.80)

    volume_dry_up = bool(
        last_10["Volume"].mean() > 0
        and prior_40["Volume"].mean() > 0
        and last_10["Volume"].mean() < prior_40["Volume"].mean() * 0.75
    )

    down_days = df[df["Close"] < df["Close"].shift(1)].tail(15)
    older_down_days = df[df["Close"] < df["Close"].shift(1)].tail(45).head(30)
    declining_selling_volume = bool(
        not down_days.empty
        and not older_down_days.empty
        and down_days["Volume"].mean() < older_down_days["Volume"].mean()
    )

    close_location = ((last_10["Close"] - last_10["Low"]) / (last_10["High"] - last_10["Low"]).replace(0, pd.NA)).mean()
    tight_closes = bool(pd.notna(close_location) and close_location > 0.55 and last_10["Close"].pct_change().abs().mean() < 0.025)

    high_52 = df.tail(min(252, len(df)))["High"].max()
    price_near_highs = bool(high_52 > 0 and df["Close"].iloc[-1] >= high_52 * 0.85)

    ema_distance = ((last_20["Close"] - last_20["EMA10"]).abs() / last_20["Close"]).mean()
    ema21_distance = ((last_20["Close"] - last_20["EMA21"]).abs() / last_20["Close"]).mean()
    tightening_near_emas = bool(pd.notna(ema_distance) and pd.notna(ema21_distance) and (ema_distance + ema21_distance) / 2 < 0.04)

    score = 0
    notes: list[str] = []
    if decreasing_sequence:
        score += 25
        notes.append("Progressively smaller contractions detected.")
    elif len(contractions) >= 2:
        score += 12
        notes.append("Multiple contractions detected, but sequence is imperfect.")

    score += min(20, len(contractions) * 6)
    flags = {
        "ATR compression": atr_compression,
        "Daily range compression": range_compression,
        "Volume dry-up": volume_dry_up,
        "Declining selling volume": declining_selling_volume,
        "Tight closes": tight_closes,
        "Price near highs": price_near_highs,
        "Tightening around 10/21 EMA": tightening_near_emas,
    }
    score += sum(8 for passed in flags.values() if passed)
    score = int(max(0, min(100, score)))
    notes.extend([name for name, passed in flags.items() if passed])

    volume_score = int(max(0, min(100, (50 if volume_dry_up else 20) + (30 if declining_selling_volume else 0))))
    return VCPResult(
        score=score,
        contractions=contractions,
        contraction_count=len(contractions),
        atr_compression=atr_compression,
        range_compression=range_compression,
        volume_dry_up=volume_dry_up,
        declining_selling_volume=declining_selling_volume,
        tight_closes=tight_closes,
        price_near_highs=price_near_highs,
        tightening_near_emas=tightening_near_emas,
        volume_score=volume_score,
        notes=notes,
    )
