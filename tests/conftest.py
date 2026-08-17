from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def make_trending_history():
    def factory(length: int = 260, start: float = 20.0, end: float = 120.0) -> pd.DataFrame:
        index = pd.bdate_range(end=datetime(2026, 8, 14), periods=length)
        base = np.linspace(start, end, length)
        wave = np.sin(np.linspace(0, 10, length)) * 1.2
        close = base + wave
        open_ = close * 0.995
        high = close * 1.018
        low = close * 0.982
        volume = np.linspace(1_400_000, 1_000_000, length)
        return pd.DataFrame(
            {
                "Open": open_,
                "High": high,
                "Low": low,
                "Close": close,
                "Volume": volume,
            },
            index=index,
        )

    return factory


@pytest.fixture
def make_downtrend_history(make_trending_history):
    def factory(length: int = 260) -> pd.DataFrame:
        return make_trending_history(length=length, start=120, end=40)

    return factory


@pytest.fixture
def make_vcp_history():
    def factory() -> pd.DataFrame:
        index = pd.bdate_range(end=datetime(2026, 8, 14), periods=120)
        rows = []
        price = 100.0
        ranges = [0.18, 0.11, 0.06]
        for i in range(30):
            close = 80 + i * 0.6
            rows.append((close * 0.99, close * 1.03, close * 0.97, close, 1_600_000))
        for segment, width in enumerate(ranges):
            center = price + segment * 4
            for i in range(30):
                drift = i / 30 * 1.5
                close = center + drift + np.sin(i / 3) * center * width * 0.05
                high = center * (1 + width / 2)
                low = center * (1 - width / 2)
                volume = 1_200_000 - segment * 220_000 - i * 4_000
                rows.append((close * 0.995, high, low, close, volume))
        return pd.DataFrame(rows[-120:], columns=["Open", "High", "Low", "Close", "Volume"], index=index)

    return factory


@pytest.fixture
def market_regime_green(make_trending_history):
    from scanner.market_regime import analyze_market_regime

    spy = make_trending_history()
    qqq = make_trending_history(start=30, end=150)
    return analyze_market_regime(spy, qqq, {"AAA": spy, "BBB": qqq})


@pytest.fixture
def future_earnings_snapshot():
    from scanner.models import FundamentalSnapshot

    def factory(days: int = 3):
        return FundamentalSnapshot(earnings_date=datetime.now() + timedelta(days=days), days_to_earnings=days, score=75)

    return factory
