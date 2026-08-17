from __future__ import annotations

from datetime import datetime
from typing import Any

from scanner.models import FundamentalSnapshot


def _coerce_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def days_until(date_value: datetime | None, now: datetime | None = None) -> int | None:
    if date_value is None:
        return None
    now = now or datetime.now()
    return (date_value.date() - now.date()).days


def score_fundamentals(snapshot: FundamentalSnapshot) -> int:
    scores: list[int] = []

    if snapshot.revenue_growth is not None:
        growth = snapshot.revenue_growth
        scores.append(100 if growth >= 0.25 else 85 if growth >= 0.12 else 65 if growth >= 0 else 30)

    if snapshot.earnings_growth is not None:
        growth = snapshot.earnings_growth
        scores.append(100 if growth >= 0.30 else 85 if growth >= 0.15 else 65 if growth >= 0 else 25)

    if snapshot.profit_margin is not None:
        margin = snapshot.profit_margin
        scores.append(95 if margin >= 0.20 else 80 if margin >= 0.10 else 60 if margin >= 0 else 35)

    if snapshot.market_cap is not None:
        cap = snapshot.market_cap
        scores.append(80 if cap >= 2_000_000_000 else 65 if cap >= 500_000_000 else 45)

    if snapshot.forward_pe is not None:
        pe = snapshot.forward_pe
        if pe <= 0:
            scores.append(40)
        elif pe <= 60:
            scores.append(75)
        else:
            scores.append(55)

    if not scores:
        return 55
    return int(round(sum(scores) / len(scores)))


def build_fundamental_snapshot(raw: dict[str, Any] | None, now: datetime | None = None) -> FundamentalSnapshot:
    raw = raw or {}
    earnings_date = raw.get("earnings_date")
    if isinstance(earnings_date, str):
        try:
            earnings_date = datetime.fromisoformat(earnings_date)
        except ValueError:
            earnings_date = None

    snapshot = FundamentalSnapshot(
        revenue_growth=_coerce_float(raw.get("revenue_growth")),
        earnings_growth=_coerce_float(raw.get("earnings_growth")),
        profit_margin=_coerce_float(raw.get("profit_margin")),
        market_cap=_coerce_float(raw.get("market_cap")),
        forward_pe=_coerce_float(raw.get("forward_pe")),
        earnings_date=earnings_date if isinstance(earnings_date, datetime) else None,
        days_to_earnings=days_until(earnings_date if isinstance(earnings_date, datetime) else None, now=now),
        sector=raw.get("sector"),
        industry=raw.get("industry"),
    )
    snapshot.score = score_fundamentals(snapshot)
    return snapshot


def is_earnings_hold(snapshot: FundamentalSnapshot, exclusion_days: int) -> bool:
    return snapshot.days_to_earnings is not None and 0 <= snapshot.days_to_earnings <= exclusion_days
