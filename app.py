from __future__ import annotations

from dataclasses import asdict

import pandas as pd
import streamlit as st

from config import ScannerConfig
from scanner.pipeline import analyze_stock, scan_universe
from ui.charts import make_stock_chart
from ui.components import (
    compact_number,
    money,
    pct,
    render_footer,
    render_global_styles,
    render_market_strip,
    render_reasons,
    render_score_breakdown,
    render_stock_cards,
    render_trend_template,
)


st.set_page_config(
    page_title="Momentum Stock Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)
render_global_styles()


def _config_from_sidebar() -> ScannerConfig:
    st.sidebar.header("Settings")
    account_size = st.sidebar.number_input("Account size", min_value=1_000.0, value=100_000.0, step=5_000.0)
    risk_pct = st.sidebar.number_input("Risk per trade (%)", min_value=0.05, max_value=5.0, value=0.50, step=0.05)
    scan_limit = st.sidebar.slider("Universe scan limit", min_value=5, max_value=300, value=80, step=5)
    max_positions = st.sidebar.number_input("Maximum positions", min_value=1, max_value=50, value=8, step=1)
    max_heat_pct = st.sidebar.number_input("Maximum portfolio heat (%)", min_value=0.5, max_value=20.0, value=3.0, step=0.5)

    st.sidebar.header("Buy Filters")
    min_score = st.sidebar.slider("Minimum BUY score", 50, 99, 80)
    min_rs = st.sidebar.slider("Minimum BUY Momentum RS", 1, 99, 80)
    max_stop = st.sidebar.slider("Maximum stop (%)", 2.0, 15.0, 8.0, step=0.5)
    earnings_window = st.sidebar.slider("Earnings exclusion days", 0, 21, 5)

    return ScannerConfig(
        account_size=account_size,
        risk_per_trade=risk_pct / 100,
        scan_limit=scan_limit,
        max_positions=int(max_positions),
        max_portfolio_heat=max_heat_pct / 100,
        min_score_buy=min_score,
        min_rs_buy=min_rs,
        max_stop_pct=max_stop / 100,
        earnings_exclusion_days=earnings_window,
    )


@st.cache_data(ttl=60 * 30, show_spinner=False)
def _run_scan(config_dict: dict, refresh_token: int):
    config = ScannerConfig(**config_dict)
    return scan_universe(config, refresh_token=refresh_token)


def _filtered(analyses, min_score, min_rs, min_vcp, max_stop, setup_types, sectors, min_price, max_price, earnings_filter):
    output = []
    for item in analyses:
        if item.score < min_score or item.momentum_rs < min_rs or item.vcp.score < min_vcp:
            continue
        if item.stop_plan.stop_pct is not None and item.stop_plan.stop_pct > max_stop:
            continue
        if setup_types and item.pivot.setup_type not in setup_types:
            continue
        if sectors and item.sector not in sectors:
            continue
        if item.current_price is not None and (item.current_price < min_price or item.current_price > max_price):
            continue
        if earnings_filter == "Exclude Holds" and item.status == "EARNINGS HOLD":
            continue
        if earnings_filter == "Only Holds" and item.status != "EARNINGS HOLD":
            continue
        output.append(item)
    return output


def _analysis_table(analyses) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Ticker": item.ticker,
                "Company": item.company,
                "Status": item.status,
                "Score": item.score,
                "Setup": item.pivot.setup_type,
                "Price": item.current_price,
                "Entry": item.pivot.entry,
                "Stop %": item.stop_plan.stop_pct,
                "Momentum RS": item.momentum_rs,
                "VCP": item.vcp.score,
                "Distance": item.distance_from_entry_pct,
                "ADV": item.avg_dollar_volume,
                "Sector": item.sector,
            }
            for item in analyses
        ]
    )


def _sort_items(items, sort_key: str, watch: bool = False):
    if sort_key == "Momentum RS":
        return sorted(items, key=lambda item: item.momentum_rs, reverse=True)
    if sort_key == "VCP Score":
        return sorted(items, key=lambda item: item.vcp.score, reverse=True)
    if sort_key == "Distance from Entry":
        return sorted(items, key=lambda item: abs(item.distance_from_entry_pct or 0))
    if sort_key == "Revenue Growth":
        return sorted(items, key=lambda item: item.fundamentals.revenue_growth or -999, reverse=True)
    if sort_key == "Stop %":
        return sorted(items, key=lambda item: item.stop_plan.stop_pct if item.stop_plan.stop_pct is not None else 999)
    if sort_key == "Average Dollar Volume":
        return sorted(items, key=lambda item: item.avg_dollar_volume or 0, reverse=True)
    if watch:
        return sorted(items, key=lambda item: abs(item.distance_from_entry_pct or 999))
    return sorted(items, key=lambda item: item.score, reverse=True)


def _render_stock_detail(analysis):
    render_stock_cards([analysis])
    render_reasons(analysis)

    col1, col2, col3 = st.columns(3)
    col1.metric("Current", money(analysis.current_price))
    col1.metric("Pivot", money(analysis.pivot.pivot))
    col1.metric("Entry", money(analysis.pivot.entry))
    col2.metric("Buy-zone high", money(analysis.pivot.entry * 1.03 if analysis.pivot.entry else None))
    col2.metric("Stop", money(analysis.stop_plan.stop))
    col2.metric("Stop %", pct(analysis.stop_plan.stop_pct))
    col3.metric("2R", money(analysis.stop_plan.target_2r))
    col3.metric("3R", money(analysis.stop_plan.target_3r))
    col3.metric("ATR", money(analysis.atr))

    st.markdown("**Fundamentals**")
    fundamentals = pd.DataFrame(
        [
            {"Metric": "Revenue Growth", "Value": pct(analysis.fundamentals.revenue_growth)},
            {"Metric": "Earnings Growth", "Value": pct(analysis.fundamentals.earnings_growth)},
            {"Metric": "Profit Margin", "Value": pct(analysis.fundamentals.profit_margin)},
            {"Metric": "Market Cap", "Value": compact_number(analysis.fundamentals.market_cap)},
            {"Metric": "Forward PE", "Value": "N/A" if analysis.fundamentals.forward_pe is None else f"{analysis.fundamentals.forward_pe:.1f}"},
            {"Metric": "Earnings", "Value": "N/A" if analysis.fundamentals.days_to_earnings is None else f"{analysis.fundamentals.days_to_earnings} days"},
        ]
    )
    st.dataframe(fundamentals, width="stretch", hide_index=True)

    chart_range = st.segmented_control("Chart Range", ["3M", "6M", "1Y", "2Y"], default="6M")
    st.plotly_chart(make_stock_chart(analysis, chart_range), width="stretch")

    render_trend_template(analysis)
    with st.expander(f"VCP: {analysis.vcp.score}/100"):
        st.write(f"Contractions: {analysis.vcp.contraction_count}")
        st.write(f"Sequence: {analysis.vcp.sequence_label}")
        st.write("\n".join(f"- {note}" for note in analysis.vcp.notes) or "No VCP strengths detected.")
    with st.expander("Score Breakdown"):
        render_score_breakdown(analysis)


def main() -> None:
    config = _config_from_sidebar()
    st.title("Momentum Stock Dashboard")

    if "refresh_token" not in st.session_state:
        st.session_state.refresh_token = 0
    if st.sidebar.button("Refresh Scan", width="stretch"):
        st.cache_data.clear()
        st.session_state.refresh_token += 1

    with st.spinner("Scanning stocks and market regime..."):
        scan_result = _run_scan(asdict(config), st.session_state.refresh_token)

    render_market_strip(scan_result.market)
    st.caption(f"Last Scan: {scan_result.scanned_at.strftime('%I:%M %p ET')}")

    st.sidebar.header("Display Filters")
    min_score = st.sidebar.slider("Minimum score", 0, 100, 0)
    min_rs = st.sidebar.slider("Minimum Momentum RS", 0, 99, 0)
    min_vcp = st.sidebar.slider("Minimum VCP", 0, 100, 0)
    max_stop = st.sidebar.slider("Max stop for display (%)", 0.0, 25.0, 25.0, step=0.5) / 100
    setup_options = sorted({item.pivot.setup_type for item in scan_result.analyses})
    sector_options = sorted({item.sector for item in scan_result.analyses if item.sector})
    setup_types = st.sidebar.multiselect("Setup Type", setup_options)
    sectors = st.sidebar.multiselect("Sector", sector_options)
    min_price, max_price = st.sidebar.slider("Price", 0.0, 1_000.0, (0.0, 1_000.0), step=1.0)
    earnings_filter = st.sidebar.selectbox("Earnings Risk", ["Include All", "Exclude Holds", "Only Holds"])

    filtered = _filtered(
        scan_result.analyses,
        min_score,
        min_rs,
        min_vcp,
        max_stop,
        setup_types,
        sectors,
        min_price,
        max_price,
        earnings_filter,
    )

    buy_tab, watch_tab, search_tab, market_tab = st.tabs(["BUY", "WATCH", "SEARCH", "MARKET"])

    with buy_tab:
        st.subheader("BUY NOW")
        buy_items = [item for item in filtered if item.status == "BUY NOW"]
        sort = st.selectbox(
            "Sort BUY",
            ["Score", "Momentum RS", "VCP Score", "Distance from Entry", "Revenue Growth", "Stop %", "Average Dollar Volume"],
            key="buy_sort",
        )
        render_stock_cards(_sort_items(buy_items, sort))
        with st.expander("Sortable Table"):
            st.dataframe(_analysis_table(_sort_items(buy_items, sort)), width="stretch", hide_index=True)

    with watch_tab:
        sort = st.selectbox(
            "Sort WATCH",
            ["Distance from Entry", "Score", "Momentum RS", "VCP Score", "Revenue Growth", "Stop %", "Average Dollar Volume"],
            key="watch_sort",
        )
        watch_statuses = ["ON DECK", "BUILDING", "EARLY BASE", "EARNINGS HOLD", "WATCH", "TRIGGERED - MARKET RISK"]
        grouped = {status: _sort_items([item for item in filtered if item.status == status], sort, watch=True) for status in watch_statuses}
        for label in watch_statuses:
            st.subheader(label)
            render_stock_cards(grouped[label], emphasize_distance=True)
        with st.expander("Sortable Table"):
            table_items = [item for status in watch_statuses for item in grouped[status]]
            st.dataframe(_analysis_table(table_items), width="stretch", hide_index=True)

    with search_tab:
        st.subheader("Ticker Search")
        ticker = st.text_input("Enter ticker", placeholder="NVDA").upper().strip()
        if ticker:
            with st.spinner(f"Analyzing {ticker}..."):
                try:
                    analysis = analyze_stock(
                        ticker=ticker,
                        benchmark_history=None,
                        market=scan_result.market,
                        config=config,
                    )
                    _render_stock_detail(analysis)
                except Exception as exc:
                    st.error(f"{ticker}: {exc}")
                    st.info("The search engine keeps the app running even when a ticker has missing or bad data.")

    with market_tab:
        st.subheader("Market Regime")
        col1, col2, col3 = st.columns(3)
        col1.metric("Market Score", f"{scan_result.market.score}/100")
        col2.metric("Regime", scan_result.market.classification)
        col3.metric("Exposure", scan_result.market.exposure)

        breadth = pd.DataFrame(
            [
                {"Breadth": "% above 20 DMA", "Value": f"{scan_result.market.breadth.get('above_20_dma', 0):.1f}%"},
                {"Breadth": "% above 50 DMA", "Value": f"{scan_result.market.breadth.get('above_50_dma', 0):.1f}%"},
                {"Breadth": "% above 200 DMA", "Value": f"{scan_result.market.breadth.get('above_200_dma', 0):.1f}%"},
            ]
        )
        st.dataframe(breadth, width="stretch", hide_index=True)

        st.subheader("Portfolio Heat")
        heat_cols = st.columns(3)
        heat_cols[0].metric("Risk per trade", f"{config.risk_per_trade * 100:.2f}%")
        heat_cols[1].metric("Maximum concurrent risk", f"{config.max_portfolio_heat * 100:.1f}%")
        full_risk_positions = min(config.max_positions, int(config.max_portfolio_heat // config.risk_per_trade))
        heat_cols[2].metric("Maximum full-risk positions", full_risk_positions)

        st.subheader("Index Checks")
        rows = []
        for ticker, details in scan_result.market.index_details.items():
            for condition, passed in details["conditions"].items():
                rows.append({"Ticker": ticker, "Condition": condition.replace("_", " ").title(), "Pass": "Yes" if passed else "No"})
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

        with st.expander("Diagnostics"):
            if scan_result.diagnostics:
                st.write("\n".join(f"- {item}" for item in scan_result.diagnostics))
            else:
                st.write("No failed symbols in the latest scan.")

    render_footer()


if __name__ == "__main__":
    main()
