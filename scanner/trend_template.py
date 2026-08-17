from __future__ import annotations

import pandas as pd

from scanner.indicators import add_indicators
from scanner.models import TrendTemplateResult


def evaluate_trend_template(price_history: pd.DataFrame) -> TrendTemplateResult:
    if price_history is None or price_history.empty or len(price_history) < 80:
        return TrendTemplateResult(
            score=0,
            total=8,
            conditions={
                "price_above_50_sma": False,
                "price_above_150_sma": False,
                "price_above_200_sma": False,
                "sma_50_above_150": False,
                "sma_150_above_200": False,
                "sma_200_rising": False,
                "price_30pct_above_52w_low": False,
                "price_within_25pct_of_52w_high": False,
            },
            insufficient_data=True,
        )

    df = add_indicators(price_history)
    last = df.iloc[-1]
    lookback = df.tail(min(252, len(df)))
    high_52w = lookback["High"].max()
    low_52w = lookback["Low"].min()

    if len(df) >= 221 and pd.notna(df["SMA200"].iloc[-22]):
        sma_200_rising = bool(last["SMA200"] > df["SMA200"].iloc[-22])
    else:
        sma_200_rising = False

    conditions = {
        "price_above_50_sma": bool(pd.notna(last["SMA50"]) and last["Close"] > last["SMA50"]),
        "price_above_150_sma": bool(pd.notna(last["SMA150"]) and last["Close"] > last["SMA150"]),
        "price_above_200_sma": bool(pd.notna(last["SMA200"]) and last["Close"] > last["SMA200"]),
        "sma_50_above_150": bool(pd.notna(last["SMA50"]) and pd.notna(last["SMA150"]) and last["SMA50"] > last["SMA150"]),
        "sma_150_above_200": bool(pd.notna(last["SMA150"]) and pd.notna(last["SMA200"]) and last["SMA150"] > last["SMA200"]),
        "sma_200_rising": sma_200_rising,
        "price_30pct_above_52w_low": bool(low_52w > 0 and last["Close"] >= low_52w * 1.30),
        "price_within_25pct_of_52w_high": bool(high_52w > 0 and last["Close"] >= high_52w * 0.75),
    }
    return TrendTemplateResult(
        score=sum(1 for passed in conditions.values() if passed),
        total=8,
        conditions=conditions,
        insufficient_data=len(df) < 221,
    )
