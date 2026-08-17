from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_SCORE_WEIGHTS = {
    "trend_template": 25,
    "relative_strength": 20,
    "vcp_base_quality": 20,
    "fundamentals": 15,
    "volume_accumulation": 10,
    "pivot_quality": 5,
    "market_regime": 5,
}


@dataclass(slots=True)
class ScannerConfig:
    entry_buffer: float = 0.001
    buy_zone_pct: float = 0.03
    on_deck_pct: float = 0.02
    building_pct: float = 0.08
    max_stop_pct: float = 0.08
    earnings_exclusion_days: int = 5

    account_size: float = 100_000.0
    risk_per_trade: float = 0.005
    max_portfolio_heat: float = 0.03
    max_positions: int = 8

    min_score_buy: int = 80
    min_trend_template_buy: int = 7
    min_rs_buy: int = 80
    min_vcp_watch: int = 45
    min_avg_dollar_volume: float = 20_000_000.0
    min_price: float = 8.0

    history_period: str = "2y"
    benchmark_ticker: str = "SPY"
    market_tickers: tuple[str, str] = ("SPY", "QQQ")
    universe_path: str = "data/us_stock_universe.csv"
    scan_limit: int = 80
    max_fundamental_fetches: int = 25

    score_weights: dict[str, int] = field(
        default_factory=lambda: DEFAULT_SCORE_WEIGHTS.copy()
    )

    market_red_cutoff: int = 50


DEFAULT_CONFIG = ScannerConfig()
