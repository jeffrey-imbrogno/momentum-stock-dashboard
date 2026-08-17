from __future__ import annotations

from config import ScannerConfig
from scanner.fundamentals import is_earnings_hold
from scanner.models import (
    FundamentalSnapshot,
    MarketRegime,
    PivotResult,
    StopPlan,
    TrendTemplateResult,
    VCPResult,
)


def build_score_breakdown(
    trend: TrendTemplateResult,
    momentum_rs: int,
    vcp: VCPResult,
    fundamentals: FundamentalSnapshot,
    pivot: PivotResult,
    market: MarketRegime,
    config: ScannerConfig,
) -> dict[str, float]:
    weights = config.score_weights
    return {
        "trend_template": trend.score / trend.total * weights["trend_template"],
        "relative_strength": momentum_rs / 100 * weights["relative_strength"],
        "vcp_base_quality": vcp.score / 100 * weights["vcp_base_quality"],
        "fundamentals": fundamentals.score / 100 * weights["fundamentals"],
        "volume_accumulation": vcp.volume_score / 100 * weights["volume_accumulation"],
        "pivot_quality": pivot.confidence / 100 * weights["pivot_quality"],
        "market_regime": market.score / 100 * weights["market_regime"],
    }


def total_score(breakdown: dict[str, float]) -> int:
    return int(round(sum(breakdown.values())))


def classify_status(
    current_price: float | None,
    score: int,
    trend: TrendTemplateResult,
    momentum_rs: int,
    pivot: PivotResult,
    stop_plan: StopPlan,
    fundamentals: FundamentalSnapshot,
    market: MarketRegime,
    config: ScannerConfig,
) -> tuple[str, float | None, list[str]]:
    reasons: list[str] = []

    if current_price is None:
        return "INSUFFICIENT DATA", None, ["No current price could be calculated."]

    if trend.insufficient_data and trend.score < 5:
        return "INSUFFICIENT DATA", None, ["Not enough price history to evaluate the full model."]

    if trend.critical_failure:
        reasons.append("One or more critical Trend Template requirements failed.")
        return "TREND FAILURE", None, reasons

    if not pivot.valid_setup or not pivot.entry:
        reasons.append("No reliable pivot was detected; the app will not manufacture an entry.")
        return "NO VALID SETUP", None, reasons

    distance = current_price / pivot.entry - 1
    if is_earnings_hold(fundamentals, config.earnings_exclusion_days) and pivot.setup_type != "POST-EARNINGS BREAKOUT":
        reasons.append(f"Earnings are within {config.earnings_exclusion_days} calendar days.")
        return "EARNINGS HOLD", distance, reasons

    if distance > config.buy_zone_pct:
        reasons.append("Price is more than the configured buy zone above entry.")
        return "EXTENDED", distance, reasons

    stop_ok = stop_plan.stop_pct is not None and stop_plan.stop_pct <= config.max_stop_pct
    quality_ok = (
        score >= config.min_score_buy
        and trend.score >= config.min_trend_template_buy
        and momentum_rs >= config.min_rs_buy
        and stop_ok
    )

    if distance >= 0:
        if quality_ok and market.score < config.market_red_cutoff:
            reasons.append("Entry has triggered, but market regime is too weak for normal BUY status.")
            return "TRIGGERED - MARKET RISK", distance, reasons
        if quality_ok:
            reasons.append("Price is inside the buy zone and all core quality filters pass.")
            return "BUY NOW", distance, reasons
        reasons.append("Entry has triggered, but one or more BUY quality filters did not pass.")
        return "WATCH", distance, reasons

    if distance >= -config.on_deck_pct:
        reasons.append("Price is within 0-2% below the planned entry.")
        return "ON DECK", distance, reasons

    if distance >= -config.building_pct:
        reasons.append("Price is 2-8% below the planned entry.")
        return "BUILDING", distance, reasons

    reasons.append("Setup is still more than 8% below entry or still developing.")
    return "EARLY BASE", distance, reasons
