from config import ScannerConfig
from scanner.models import FundamentalSnapshot, PivotResult, StopPlan, TrendTemplateResult
from scanner.scoring import classify_status


def _trend(score=8):
    return TrendTemplateResult(
        score=score,
        total=8,
        conditions={
            "price_above_50_sma": score >= 7,
            "price_above_150_sma": score >= 7,
            "price_above_200_sma": score >= 7,
            "sma_50_above_150": score >= 7,
            "sma_150_above_200": score >= 7,
            "sma_200_rising": score >= 7,
            "price_30pct_above_52w_low": score >= 7,
            "price_within_25pct_of_52w_high": score >= 7,
        },
    )


def _pivot(valid=True):
    return PivotResult("VCP PIVOT" if valid else "NO VALID SETUP", 100.0 if valid else None, 100.1 if valid else None, valid, 85)


def _stop(stop_pct=0.05):
    return StopPlan(95.0, 5.1, stop_pct, 110.0, 115.0, 98, 9_809.8, 500, {})


def test_buy_now_classification(market_regime_green):
    status, distance, reasons = classify_status(
        101.0,
        90,
        _trend(),
        92,
        _pivot(),
        _stop(),
        FundamentalSnapshot(score=70),
        market_regime_green,
        ScannerConfig(),
    )

    assert status == "BUY NOW"
    assert distance is not None
    assert reasons


def test_watch_tiers_and_extended(market_regime_green):
    config = ScannerConfig()

    assert classify_status(99.0, 90, _trend(), 92, _pivot(), _stop(), FundamentalSnapshot(score=70), market_regime_green, config)[0] == "ON DECK"
    assert classify_status(94.0, 90, _trend(), 92, _pivot(), _stop(), FundamentalSnapshot(score=70), market_regime_green, config)[0] == "BUILDING"
    assert classify_status(88.0, 90, _trend(), 92, _pivot(), _stop(), FundamentalSnapshot(score=70), market_regime_green, config)[0] == "EARLY BASE"
    assert classify_status(105.0, 90, _trend(), 92, _pivot(), _stop(), FundamentalSnapshot(score=70), market_regime_green, config)[0] == "EXTENDED"


def test_no_valid_setup_and_earnings_hold(market_regime_green, future_earnings_snapshot):
    config = ScannerConfig()

    no_setup = classify_status(100.0, 90, _trend(), 92, _pivot(False), _stop(), FundamentalSnapshot(score=70), market_regime_green, config)
    hold = classify_status(101.0, 90, _trend(), 92, _pivot(), _stop(), future_earnings_snapshot(), market_regime_green, config)

    assert no_setup[0] == "NO VALID SETUP"
    assert hold[0] == "EARNINGS HOLD"
