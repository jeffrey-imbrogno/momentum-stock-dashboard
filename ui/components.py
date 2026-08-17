from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from scanner.models import MarketRegime, StockAnalysis


STATUS_CLASSES = {
    "BUY NOW": "status-green",
    "TRIGGERED - MARKET RISK": "status-yellow",
    "ON DECK": "status-yellow",
    "BUILDING": "status-yellow",
    "WATCH": "status-yellow",
    "EARLY BASE": "status-gray",
    "EARNINGS HOLD": "status-red",
    "EXTENDED": "status-red",
    "TREND FAILURE": "status-red",
    "NO VALID SETUP": "status-gray",
    "INSUFFICIENT DATA": "status-gray",
}


def render_global_styles() -> None:
    st.html(
        """
        <style>
        :root {
            --bg: #f7f8fb;
            --card: #ffffff;
            --text: #17202a;
            --muted: #5b6472;
            --line: #d9dee8;
            --green: #147d4f;
            --yellow: #9a6b00;
            --red: #b42318;
            --gray: #5d6673;
        }
        .main .block-container {
            padding-top: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
            max-width: 1180px;
        }
        h1, h2, h3 {
            letter-spacing: 0;
        }
        .market-strip {
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 0.75rem;
            align-items: center;
            padding: 0.85rem 1rem;
            border: 1px solid var(--line);
            background: var(--card);
            border-radius: 8px;
            margin-bottom: 0.75rem;
        }
        .market-title {
            font-size: 0.78rem;
            color: var(--muted);
            font-weight: 700;
            text-transform: uppercase;
        }
        .market-score {
            font-size: 1.4rem;
            font-weight: 800;
            color: var(--text);
        }
        .card-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 0.75rem;
        }
        .stock-card {
            border: 1px solid var(--line);
            background: var(--card);
            border-radius: 8px;
            padding: 0.9rem;
            min-width: 0;
            max-width: 100%;
            box-sizing: border-box;
            overflow: hidden;
        }
        .card-head {
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 0.5rem;
            align-items: start;
            border-bottom: 1px solid var(--line);
            padding-bottom: 0.65rem;
            margin-bottom: 0.7rem;
        }
        .ticker {
            font-size: 1.35rem;
            font-weight: 900;
            color: var(--text);
            line-height: 1.1;
        }
        .company {
            color: var(--muted);
            font-size: 0.84rem;
            margin-top: 0.18rem;
            overflow-wrap: anywhere;
        }
        .score-pill, .status-pill {
            border-radius: 6px;
            font-weight: 800;
            padding: 0.26rem 0.45rem;
            text-align: center;
            white-space: nowrap;
            font-size: 0.8rem;
        }
        .score-pill {
            color: #17202a;
            background: #eef1f6;
            margin-bottom: 0.25rem;
        }
        .status-green { color: #ffffff; background: var(--green); }
        .status-yellow { color: #1f2933; background: #ffd56a; }
        .status-red { color: #ffffff; background: var(--red); }
        .status-gray { color: #ffffff; background: var(--gray); }
        .setup-type {
            font-size: 0.78rem;
            font-weight: 800;
            color: var(--muted);
            text-transform: uppercase;
            margin: 0.15rem 0 0.55rem;
        }
        .kv {
            display: grid;
            grid-template-columns: minmax(7rem, 1fr) auto;
            gap: 0.35rem 0.75rem;
            font-size: 0.9rem;
            line-height: 1.35;
        }
        .kv div:nth-child(odd) { color: var(--muted); }
        .kv div:nth-child(even) { color: var(--text); font-weight: 700; text-align: right; }
        .badges {
            display: flex;
            flex-wrap: wrap;
            gap: 0.35rem;
            margin-top: 0.75rem;
        }
        .badge {
            border: 1px solid var(--line);
            border-radius: 6px;
            padding: 0.22rem 0.42rem;
            font-size: 0.76rem;
            color: var(--text);
            background: #fbfcfe;
            white-space: nowrap;
        }
        .reason-list {
            margin: 0.35rem 0 0;
            padding-left: 1.1rem;
        }
        .footer {
            color: var(--muted);
            font-size: 0.78rem;
            border-top: 1px solid var(--line);
            margin-top: 2rem;
            padding-top: 0.8rem;
        }
        @media (max-width: 640px) {
            .main .block-container {
                padding-left: 0.65rem;
                padding-right: 0.65rem;
                max-width: 100vw;
                overflow-x: hidden;
            }
            .card-grid {
                grid-template-columns: minmax(0, 1fr);
                gap: 0.6rem;
                width: calc(100vw - 2rem);
                max-width: calc(100vw - 2rem);
                overflow-x: hidden;
            }
            .stock-card {
                padding: 0.78rem;
                width: 100%;
                max-width: calc(100vw - 2rem);
            }
            .ticker {
                font-size: 1.2rem;
            }
            .kv {
                grid-template-columns: minmax(6.6rem, 1fr) auto;
                font-size: 0.86rem;
            }
            .market-strip {
                grid-template-columns: 1fr;
            }
            .market-score {
                font-size: 1.2rem;
            }
        }
        </style>
        """
    )


def money(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"${value:,.2f}"


def pct(value: float | None, signed: bool = False) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    prefix = "+" if signed and value > 0 else ""
    return f"{prefix}{value * 100:.1f}%"


def compact_number(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    if abs_value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs_value >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:,.0f}"


def render_market_strip(market: MarketRegime) -> None:
    st.html(
        f"""
        <div class="market-strip">
            <div>
                <div class="market-title">Market</div>
                <div class="market-score">{escape(market.classification)} - {market.score}/100</div>
            </div>
            <div>
                <div class="market-title">Suggested Exposure</div>
                <div class="market-score">{escape(market.exposure)}</div>
            </div>
        </div>
        """
    )


def _status_class(status: str) -> str:
    return STATUS_CLASSES.get(status, "status-gray")


def stock_card_html(analysis: StockAnalysis, emphasize_distance: bool = False) -> str:
    setup = analysis.pivot.setup_type
    entry = analysis.pivot.entry
    buy_zone_high = entry * 1.03 if entry else None
    stop = analysis.stop_plan.stop
    target_1 = analysis.stop_plan.target_2r
    target_2 = analysis.stop_plan.target_3r
    days = analysis.fundamentals.days_to_earnings
    earnings = "N/A" if days is None else f"{days} days"
    distance_label = "Distance to Entry" if emphasize_distance else "Distance from Entry"

    return (
        '<div class="stock-card">'
        '<div class="card-head">'
        "<div>"
        f'<div class="ticker">{escape(analysis.ticker)}</div>'
        f'<div class="company">{escape(analysis.company or analysis.ticker)}</div>'
        "</div>"
        "<div>"
        f'<div class="score-pill">{analysis.score}</div>'
        f'<div class="status-pill {_status_class(analysis.status)}">{escape(analysis.status)}</div>'
        "</div>"
        "</div>"
        f'<div class="setup-type">{escape(setup)}</div>'
        '<div class="kv">'
        f"<div>Current</div><div>{money(analysis.current_price)}</div>"
        f"<div>Entry</div><div>{money(entry)}</div>"
        f"<div>Buy Zone</div><div>{money(entry)} - {money(buy_zone_high)}</div>"
        f"<div>Stop</div><div>{money(stop)}</div>"
        f"<div>Risk</div><div>{pct(analysis.stop_plan.stop_pct)}</div>"
        f"<div>Target 1</div><div>{money(target_1)}</div>"
        f"<div>Target 2</div><div>{money(target_2)}</div>"
        f"<div>Shares</div><div>{analysis.stop_plan.shares}</div>"
        f"<div>{distance_label}</div><div>{pct(analysis.distance_from_entry_pct, signed=True)}</div>"
        f"<div>Earnings</div><div>{escape(earnings)}</div>"
        "</div>"
        '<div class="badges">'
        f'<span class="badge">VCP {analysis.vcp.score}</span>'
        f'<span class="badge">TT {analysis.trend_template.label}</span>'
        f'<span class="badge">RS {analysis.momentum_rs}</span>'
        f'<span class="badge">ADV {compact_number(analysis.avg_dollar_volume)}</span>'
        "</div>"
        "</div>"
    )


def render_stock_cards(analyses: list[StockAnalysis], emphasize_distance: bool = False) -> None:
    if not analyses:
        st.info("No stocks match the current filters.")
        return
    cards = "".join(stock_card_html(item, emphasize_distance=emphasize_distance) for item in analyses)
    st.html(f'<div class="card-grid">{cards}</div>')


def render_reasons(analysis: StockAnalysis) -> None:
    st.subheader(f"{analysis.ticker} - {analysis.status}")
    if analysis.reasons:
        st.markdown("**Why**")
        st.markdown("\n".join(f"- {reason}" for reason in analysis.reasons))
    if analysis.pivot.rationale:
        st.markdown("**Setup Notes**")
        st.markdown("\n".join(f"- {reason}" for reason in analysis.pivot.rationale))
    if analysis.warnings:
        st.warning("\n".join(analysis.warnings))


def render_trend_template(analysis: StockAnalysis) -> None:
    with st.expander(f"Trend Template: {analysis.trend_template.label}"):
        rows = [
            {"Condition": key.replace("_", " ").title(), "Pass": "Yes" if passed else "No"}
            for key, passed in analysis.trend_template.conditions.items()
        ]
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def render_score_breakdown(analysis: StockAnalysis) -> None:
    breakdown = pd.DataFrame(
        [
            {"Component": key.replace("_", " ").title(), "Points": round(value, 1)}
            for key, value in analysis.score_breakdown.items()
        ]
    )
    st.dataframe(breakdown, width="stretch", hide_index=True)


def render_footer() -> None:
    st.html(
        """
        <div class="footer">
        For research and educational purposes only. Not financial advice.
        Market data may be delayed or incomplete. Stops do not guarantee execution prices.
        </div>
        """
    )
