from __future__ import annotations

import math

import pandas as pd

from config import ScannerConfig
from scanner.indicators import add_indicators
from scanner.models import PivotResult, StopPlan


def calculate_targets(entry: float, stop: float) -> tuple[float, float]:
    risk = entry - stop
    return float(entry + 2 * risk), float(entry + 3 * risk)


def calculate_position_size(
    entry: float, stop: float, account_size: float, risk_per_trade: float
) -> tuple[int, float, float]:
    dollar_risk = account_size * risk_per_trade
    risk_per_share = entry - stop
    if risk_per_share <= 0:
        return 0, 0.0, dollar_risk
    shares = int(dollar_risk // risk_per_share)
    return shares, shares * entry, dollar_risk


def calculate_stop_plan(
    price_history: pd.DataFrame,
    pivot: PivotResult,
    config: ScannerConfig,
) -> StopPlan:
    dollar_risk = config.account_size * config.risk_per_trade
    if not pivot.valid_setup or not pivot.entry or price_history is None or price_history.empty:
        return StopPlan(
            stop=None,
            risk_per_share=None,
            stop_pct=None,
            target_2r=None,
            target_3r=None,
            shares=0,
            position_value=None,
            dollar_risk=dollar_risk,
            candidates={},
        )

    df = add_indicators(price_history)
    entry = float(pivot.entry)
    recent = df.tail(35)
    last = df.iloc[-1]

    candidates: dict[str, float] = {
        "Recent swing low": float(recent.tail(20)["Low"].min()),
        "1.5 ATR": entry - float(last["ATR14"] or 0) * 1.5,
        "Final contraction low": float(recent.tail(25)["Low"].min()),
    }
    if pd.notna(last["EMA21"]):
        candidates["21 EMA"] = float(last["EMA21"] * 0.985)

    candidates = {
        label: value
        for label, value in candidates.items()
        if value is not None and math.isfinite(value) and 0 < value < entry
    }
    if not candidates:
        return StopPlan(
            stop=None,
            risk_per_share=None,
            stop_pct=None,
            target_2r=None,
            target_3r=None,
            shares=0,
            position_value=None,
            dollar_risk=dollar_risk,
            candidates={},
        )

    within_limit = {
        label: value
        for label, value in candidates.items()
        if (entry - value) / entry <= config.max_stop_pct
    }
    pool = within_limit or candidates
    stop = max(pool.values())
    risk_per_share = entry - stop
    stop_pct = risk_per_share / entry
    target_2r, target_3r = calculate_targets(entry, stop)
    shares, position_value, dollar_risk = calculate_position_size(
        entry, stop, config.account_size, config.risk_per_trade
    )

    return StopPlan(
        stop=float(stop),
        risk_per_share=float(risk_per_share),
        stop_pct=float(stop_pct),
        target_2r=target_2r,
        target_3r=target_3r,
        shares=shares,
        position_value=position_value,
        dollar_risk=dollar_risk,
        candidates=candidates,
    )
