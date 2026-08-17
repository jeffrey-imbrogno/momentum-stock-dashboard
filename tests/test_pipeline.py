import pandas as pd

from config import ScannerConfig
from scanner.pipeline import analyze_stock, scan_universe


def test_search_analysis_does_not_require_universe_membership(make_trending_history, market_regime_green):
    history = make_trending_history()
    analysis = analyze_stock(
        ticker="ZZZZ",
        company="Outside Universe",
        price_history=history,
        benchmark_history=history,
        market=market_regime_green,
        raw_fundamentals={},
        config=ScannerConfig(),
    )

    assert analysis.ticker == "ZZZZ"
    assert analysis.status in {
        "BUY NOW",
        "WATCH",
        "ON DECK",
        "BUILDING",
        "EARLY BASE",
        "EXTENDED",
        "NO VALID SETUP",
        "TREND FAILURE",
    }


def test_bad_ticker_does_not_break_scan(monkeypatch, make_trending_history):
    universe = pd.DataFrame(
        [
            {"ticker": "GOOD", "company": "Good Co", "exchange": "NASDAQ", "sector": "Technology", "industry": "Software"},
            {"ticker": "BAD", "company": "Bad Co", "exchange": "NASDAQ", "sector": "Technology", "industry": "Software"},
        ]
    )

    def fake_universe(config):
        return universe

    def fake_history(ticker, period="2y", interval="1d"):
        if ticker == "BAD":
            raise RuntimeError("bad symbol")
        return make_trending_history()

    monkeypatch.setattr("scanner.pipeline.get_universe", fake_universe)
    monkeypatch.setattr("scanner.pipeline.fetch_price_history", fake_history)
    monkeypatch.setattr("scanner.pipeline.fetch_fundamentals", lambda ticker: {})

    result = scan_universe(ScannerConfig(scan_limit=2, min_avg_dollar_volume=1))

    assert any(item.ticker == "GOOD" for item in result.analyses)
    assert any("BAD" in message for message in result.diagnostics)
