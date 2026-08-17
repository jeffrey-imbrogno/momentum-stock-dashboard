from __future__ import annotations

import math

import pandas as pd


HORIZONS = {
    "3m": (63, 0.40),
    "6m": (126, 0.30),
    "12m": (252, 0.30),
}


def weighted_relative_performance(
    stock_history: pd.DataFrame, benchmark_history: pd.DataFrame
) -> float | None:
    if stock_history is None or benchmark_history is None:
        return None
    if stock_history.empty or benchmark_history.empty:
        return None

    stock_close = stock_history["Close"].dropna()
    benchmark_close = benchmark_history["Close"].dropna()
    aligned = pd.concat([stock_close, benchmark_close], axis=1, join="inner").dropna()
    aligned.columns = ["stock", "benchmark"]
    if len(aligned) < 65:
        return None

    weighted_sum = 0.0
    weight_used = 0.0
    for sessions, weight in HORIZONS.values():
        if len(aligned) <= sessions:
            continue
        stock_return = aligned["stock"].iloc[-1] / aligned["stock"].iloc[-sessions] - 1
        benchmark_return = aligned["benchmark"].iloc[-1] / aligned["benchmark"].iloc[-sessions] - 1
        weighted_sum += (stock_return - benchmark_return) * weight
        weight_used += weight

    if weight_used == 0:
        return None
    return weighted_sum / weight_used


def score_from_relative_performance(relative_performance: float | None) -> int:
    if relative_performance is None or math.isnan(relative_performance):
        return 50
    score = 50 + relative_performance * 220
    return int(max(1, min(99, round(score))))


def rank_rs_scores(raw_scores: dict[str, float | None]) -> dict[str, int]:
    valid = pd.Series({k: v for k, v in raw_scores.items() if v is not None}).dropna()
    if valid.empty:
        return {ticker: 50 for ticker in raw_scores}

    ranks = valid.rank(method="average", pct=True)
    ranked = {ticker: int(max(1, min(99, round(rank * 99)))) for ticker, rank in ranks.items()}
    for ticker in raw_scores:
        ranked.setdefault(ticker, 50)
    return ranked
