from __future__ import annotations

import pandas as pd

from scanner.indicators import add_indicators
from scanner.models import MarketRegime


def _score_index(history: pd.DataFrame) -> dict[str, object]:
    if history is None or history.empty or len(history) < 80:
        return {
            "score": 0,
            "conditions": {
                "price_above_50_sma": False,
                "price_above_200_sma": False,
                "sma_50_above_200": False,
                "sma_200_rising": False,
                "near_52w_high": False,
            },
        }

    df = add_indicators(history)
    last = df.iloc[-1]
    high_52 = df.tail(min(252, len(df)))["High"].max()
    sma_200_rising = bool(len(df) >= 221 and pd.notna(df["SMA200"].iloc[-22]) and last["SMA200"] > df["SMA200"].iloc[-22])
    conditions = {
        "price_above_50_sma": bool(pd.notna(last["SMA50"]) and last["Close"] > last["SMA50"]),
        "price_above_200_sma": bool(pd.notna(last["SMA200"]) and last["Close"] > last["SMA200"]),
        "sma_50_above_200": bool(pd.notna(last["SMA50"]) and pd.notna(last["SMA200"]) and last["SMA50"] > last["SMA200"]),
        "sma_200_rising": sma_200_rising,
        "near_52w_high": bool(high_52 > 0 and last["Close"] >= high_52 * 0.85),
    }
    return {"score": int(sum(conditions.values()) / len(conditions) * 100), "conditions": conditions}


def _calculate_breadth(histories: dict[str, pd.DataFrame]) -> dict[str, float]:
    counts = {"above_20_dma": 0, "above_50_dma": 0, "above_200_dma": 0}
    total = 0
    for history in histories.values():
        if history is None or history.empty or len(history) < 50:
            continue
        df = add_indicators(history)
        last = df.iloc[-1]
        total += 1
        if pd.notna(last["SMA20"]) and last["Close"] > last["SMA20"]:
            counts["above_20_dma"] += 1
        if pd.notna(last["SMA50"]) and last["Close"] > last["SMA50"]:
            counts["above_50_dma"] += 1
        if pd.notna(last["SMA200"]) and last["Close"] > last["SMA200"]:
            counts["above_200_dma"] += 1

    if total == 0:
        return {"above_20_dma": 0.0, "above_50_dma": 0.0, "above_200_dma": 0.0}
    return {key: round(value / total * 100, 1) for key, value in counts.items()}


def classify_market(score: int) -> tuple[str, str]:
    if score >= 80:
        return "GREEN", "AGGRESSIVE"
    if score >= 65:
        return "YELLOW-GREEN", "NORMAL"
    if score >= 50:
        return "YELLOW", "REDUCED"
    return "RED", "DEFENSIVE"


def analyze_market_regime(
    spy_history: pd.DataFrame | None,
    qqq_history: pd.DataFrame | None,
    stock_histories: dict[str, pd.DataFrame] | None = None,
) -> MarketRegime:
    index_details = {
        "SPY": _score_index(spy_history if spy_history is not None else pd.DataFrame()),
        "QQQ": _score_index(qqq_history if qqq_history is not None else pd.DataFrame()),
    }
    breadth = _calculate_breadth(stock_histories or {})
    index_score = sum(detail["score"] for detail in index_details.values()) / len(index_details)
    breadth_score = (
        breadth.get("above_20_dma", 0) * 0.25
        + breadth.get("above_50_dma", 0) * 0.35
        + breadth.get("above_200_dma", 0) * 0.40
    )
    score = int(round(index_score * 0.70 + breadth_score * 0.30))
    classification, exposure = classify_market(score)
    return MarketRegime(
        score=score,
        classification=classification,
        exposure=exposure,
        index_details=index_details,
        breadth=breadth,
    )
