from __future__ import annotations

from datetime import datetime
from functools import lru_cache, wraps
from pathlib import Path
from typing import Any

import pandas as pd


def cache_data(**kwargs: Any):
    """Use Streamlit caching when available, otherwise fall back to lru_cache."""

    def decorator(func):
        try:
            import streamlit as st

            return st.cache_data(**kwargs)(func)
        except Exception:
            cached = lru_cache(maxsize=64)(func)

            @wraps(func)
            def wrapper(*args, **inner_kwargs):
                return cached(*args, **inner_kwargs)

            return wrapper

    return decorator


def normalize_price_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()

    df = frame.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[-1] if col[-1] in {"Open", "High", "Low", "Close", "Volume"} else col[0] for col in df.columns]

    rename_map = {
        "Adj Close": "Close",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    }
    df = df.rename(columns=rename_map)

    required = ["Open", "High", "Low", "Close", "Volume"]
    if not set(required).issubset(df.columns):
        return pd.DataFrame()

    df = df[required].dropna(subset=["Open", "High", "Low", "Close"])
    df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df.sort_index()
    return df


@cache_data(ttl=60 * 60 * 4, show_spinner=False)
def load_universe(path: str) -> pd.DataFrame:
    universe_path = Path(path)
    if universe_path.exists():
        df = pd.read_csv(universe_path)
    else:
        df = pd.DataFrame(
            [
                {"ticker": "NVDA", "company": "NVIDIA Corp.", "exchange": "NASDAQ", "sector": "Technology", "industry": "Semiconductors"},
                {"ticker": "PLTR", "company": "Palantir Technologies", "exchange": "NYSE", "sector": "Technology", "industry": "Software"},
                {"ticker": "RKLB", "company": "Rocket Lab USA", "exchange": "NASDAQ", "sector": "Industrials", "industry": "Aerospace"},
            ]
        )

    expected = ["ticker", "company", "exchange", "sector", "industry"]
    for column in expected:
        if column not in df.columns:
            df[column] = ""
    df = df[expected].copy()
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df = df[df["ticker"].ne("")]
    return df.drop_duplicates(subset=["ticker"]).reset_index(drop=True)


@cache_data(ttl=60 * 60 * 4, show_spinner=False)
def fetch_price_history(ticker: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("yfinance is not installed. Run pip install -r requirements.txt.") from exc

    symbol = ticker.upper().strip()
    frame = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    return normalize_price_frame(frame)


@cache_data(ttl=60 * 60 * 12, show_spinner=False)
def fetch_fundamentals(ticker: str) -> dict[str, Any]:
    try:
        import yfinance as yf
    except ImportError:
        return {}

    symbol = ticker.upper().strip()
    try:
        stock = yf.Ticker(symbol)
        info = stock.info or {}
    except Exception:
        return {}

    earnings_date = None
    try:
        dates = stock.get_earnings_dates(limit=1)
        if dates is not None and not dates.empty:
            earnings_date = dates.index[0].to_pydatetime().replace(tzinfo=None)
    except Exception:
        earnings_date = None

    return {
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "profit_margin": info.get("profitMargins"),
        "market_cap": info.get("marketCap"),
        "forward_pe": info.get("forwardPE"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "earnings_date": earnings_date,
        "fetched_at": datetime.utcnow().isoformat(timespec="seconds"),
    }
