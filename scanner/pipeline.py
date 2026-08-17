from __future__ import annotations

from datetime import datetime

import pandas as pd

from config import ScannerConfig
from data.cache import fetch_fundamentals, fetch_price_history
from scanner.fundamentals import build_fundamental_snapshot
from scanner.indicators import add_indicators, latest_number
from scanner.market_regime import analyze_market_regime
from scanner.models import MarketRegime, ScanResult, StockAnalysis
from scanner.pivots import detect_pivot
from scanner.relative_strength import (
    rank_rs_scores,
    score_from_relative_performance,
    weighted_relative_performance,
)
from scanner.scoring import build_score_breakdown, classify_status, total_score
from scanner.trade_planner import calculate_stop_plan
from scanner.trend_template import evaluate_trend_template
from scanner.universe import apply_universe_filters, get_universe
from scanner.vcp import analyze_vcp


def _safe_current_price(history: pd.DataFrame) -> float | None:
    if history is None or history.empty:
        return None
    close = history["Close"].dropna()
    if close.empty:
        return None
    return float(close.iloc[-1])


def _avg_dollar_volume(history: pd.DataFrame, sessions: int = 20) -> float | None:
    if history is None or history.empty:
        return None
    df = add_indicators(history)
    value = df["DollarVolume"].tail(sessions).mean()
    if pd.isna(value):
        return None
    return float(value)


def build_market_from_histories(
    histories: dict[str, pd.DataFrame],
    config: ScannerConfig,
) -> MarketRegime:
    spy = histories.get("SPY")
    qqq = histories.get("QQQ")
    return analyze_market_regime(spy, qqq, histories)


def analyze_stock(
    ticker: str,
    company: str = "",
    exchange: str = "",
    sector: str = "",
    industry: str = "",
    price_history: pd.DataFrame | None = None,
    benchmark_history: pd.DataFrame | None = None,
    market: MarketRegime | None = None,
    rs_score: int | None = None,
    raw_fundamentals: dict | None = None,
    config: ScannerConfig | None = None,
) -> StockAnalysis:
    config = config or ScannerConfig()
    ticker = ticker.upper().strip()
    warnings: list[str] = []

    if price_history is None:
        price_history = fetch_price_history(ticker, period=config.history_period)
    if benchmark_history is None:
        try:
            benchmark_history = fetch_price_history(config.benchmark_ticker, period=config.history_period)
        except Exception:
            benchmark_history = pd.DataFrame()

    current_price = _safe_current_price(price_history)
    trend = evaluate_trend_template(price_history)
    vcp = analyze_vcp(price_history)
    pivot = detect_pivot(price_history, trend, vcp, config)
    stop_plan = calculate_stop_plan(price_history, pivot, config)
    avg_dollar_volume = _avg_dollar_volume(price_history)
    atr = latest_number(add_indicators(price_history), "ATR14") if price_history is not None and not price_history.empty else None

    if rs_score is None:
        raw_rs = weighted_relative_performance(price_history, benchmark_history)
        rs_score = score_from_relative_performance(raw_rs)

    if raw_fundamentals is None:
        try:
            raw_fundamentals = fetch_fundamentals(ticker)
        except Exception as exc:
            warnings.append(f"Fundamentals unavailable: {exc}")
            raw_fundamentals = {}
    fundamentals = build_fundamental_snapshot(raw_fundamentals)
    if not sector and fundamentals.sector:
        sector = fundamentals.sector
    if not industry and fundamentals.industry:
        industry = fundamentals.industry

    if market is None:
        market = analyze_market_regime(benchmark_history, pd.DataFrame(), {ticker: price_history})

    breakdown = build_score_breakdown(trend, rs_score, vcp, fundamentals, pivot, market, config)
    score = total_score(breakdown)
    status, distance, reasons = classify_status(
        current_price,
        score,
        trend,
        rs_score,
        pivot,
        stop_plan,
        fundamentals,
        market,
        config,
    )

    if avg_dollar_volume is not None and avg_dollar_volume < config.min_avg_dollar_volume:
        warnings.append("Average dollar volume is below the configured liquidity threshold.")
    if current_price is not None and current_price < config.min_price:
        warnings.append("Price is below the configured minimum price threshold.")

    return StockAnalysis(
        ticker=ticker,
        company=company or ticker,
        exchange=exchange,
        sector=sector,
        industry=industry,
        status=status,
        current_price=current_price,
        score=score,
        score_breakdown=breakdown,
        trend_template=trend,
        momentum_rs=rs_score,
        vcp=vcp,
        pivot=pivot,
        stop_plan=stop_plan,
        fundamentals=fundamentals,
        distance_from_entry_pct=distance,
        avg_dollar_volume=avg_dollar_volume,
        atr=atr,
        reasons=reasons,
        warnings=warnings,
        history=price_history,
    )


def scan_universe(config: ScannerConfig | None = None, refresh_token: int | None = None) -> ScanResult:
    del refresh_token
    config = config or ScannerConfig()
    universe = apply_universe_filters(get_universe(config)).head(config.scan_limit)
    diagnostics: list[str] = []
    histories: dict[str, pd.DataFrame] = {}

    symbols = set(universe["ticker"].tolist()) | set(config.market_tickers) | {config.benchmark_ticker}
    for ticker in sorted(symbols):
        try:
            history = fetch_price_history(ticker, period=config.history_period)
            if history.empty:
                diagnostics.append(f"{ticker}: no price history returned.")
                continue
            histories[ticker] = history
        except Exception as exc:
            diagnostics.append(f"{ticker}: {exc}")

    raw_rs = {
        ticker: weighted_relative_performance(history, histories.get(config.benchmark_ticker, pd.DataFrame()))
        for ticker, history in histories.items()
        if ticker in set(universe["ticker"])
    }
    rs_scores = rank_rs_scores(raw_rs)
    market = build_market_from_histories(histories, config)

    analyses: list[StockAnalysis] = []
    fundamental_fetches = 0
    for row in universe.itertuples(index=False):
        ticker = row.ticker
        history = histories.get(ticker)
        if history is None or history.empty:
            continue

        current_price = _safe_current_price(history)
        adv = _avg_dollar_volume(history)
        if current_price is None or current_price < config.min_price:
            diagnostics.append(f"{ticker}: skipped by minimum price filter.")
            continue
        if adv is None or adv < config.min_avg_dollar_volume:
            diagnostics.append(f"{ticker}: skipped by liquidity filter.")
            continue

        raw_fundamentals = {}
        if fundamental_fetches < config.max_fundamental_fetches:
            try:
                raw_fundamentals = fetch_fundamentals(ticker)
            except Exception as exc:
                diagnostics.append(f"{ticker}: fundamentals unavailable ({exc}).")
            fundamental_fetches += 1

        try:
            analyses.append(
                analyze_stock(
                    ticker=ticker,
                    company=row.company,
                    exchange=row.exchange,
                    sector=row.sector,
                    industry=row.industry,
                    price_history=history,
                    benchmark_history=histories.get(config.benchmark_ticker, pd.DataFrame()),
                    market=market,
                    rs_score=rs_scores.get(ticker, 50),
                    raw_fundamentals=raw_fundamentals,
                    config=config,
                )
            )
        except Exception as exc:
            diagnostics.append(f"{ticker}: analysis failed ({exc}).")

    return ScanResult(
        analyses=sorted(analyses, key=lambda item: item.score, reverse=True),
        market=market,
        diagnostics=diagnostics,
        scanned_at=datetime.now(),
    )
