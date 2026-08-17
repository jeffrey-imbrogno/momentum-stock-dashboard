from __future__ import annotations

import pandas as pd


def true_range(frame: pd.DataFrame) -> pd.Series:
    high_low = frame["High"] - frame["Low"]
    high_prev_close = (frame["High"] - frame["Close"].shift(1)).abs()
    low_prev_close = (frame["Low"] - frame["Close"].shift(1)).abs()
    return pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)


def average_true_range(frame: pd.DataFrame, window: int = 14) -> pd.Series:
    return true_range(frame).rolling(window).mean()


def add_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    df["EMA10"] = df["Close"].ewm(span=10, adjust=False).mean()
    df["EMA21"] = df["Close"].ewm(span=21, adjust=False).mean()
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA150"] = df["Close"].rolling(150).mean()
    df["SMA200"] = df["Close"].rolling(200).mean()
    df["ATR14"] = average_true_range(df, 14)
    df["DollarVolume"] = df["Close"] * df["Volume"]
    return df


def latest_number(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty or column not in frame.columns:
        return None
    value = frame[column].dropna().iloc[-1] if not frame[column].dropna().empty else None
    return None if value is None or pd.isna(value) else float(value)


def percent(value: float | None) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value) * 100
