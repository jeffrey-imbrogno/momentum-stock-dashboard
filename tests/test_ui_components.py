from scanner.models import (
    FundamentalSnapshot,
    PivotResult,
    StockAnalysis,
    StopPlan,
    TrendTemplateResult,
    VCPResult,
)
from ui.components import stock_card_html


def _analysis(status: str) -> StockAnalysis:
    valid = status != "NO VALID SETUP"
    return StockAnalysis(
        ticker="TST",
        company="Test Corp.",
        exchange="NASDAQ",
        sector="Technology",
        industry="Software",
        status=status,
        current_price=101.0,
        score=91,
        score_breakdown={},
        trend_template=TrendTemplateResult(8, 8, {f"condition_{i}": True for i in range(8)}),
        momentum_rs=94,
        vcp=VCPResult(82, [18, 11, 6], 3, True, True, True, True, True, True, True, 80),
        pivot=PivotResult("VCP PIVOT" if valid else "NO VALID SETUP", 100.0 if valid else None, 100.1 if valid else None, valid, 88),
        stop_plan=StopPlan(96.0 if valid else None, 4.1 if valid else None, 0.041 if valid else None, 108.3 if valid else None, 112.4 if valid else None, 121 if valid else 0, 12_221.0 if valid else None, 500.0),
        fundamentals=FundamentalSnapshot(days_to_earnings=27, score=75),
        distance_from_entry_pct=0.009 if valid else None,
        avg_dollar_volume=150_000_000,
        atr=3.2,
        history=None,
    )


def test_stock_cards_render_requested_status_examples():
    for status in ["BUY NOW", "WATCH", "EXTENDED", "NO VALID SETUP"]:
        html = stock_card_html(_analysis(status))

        assert "TST" in html
        assert status in html
        assert "VCP 82" in html
        assert "TT 8/8" in html
