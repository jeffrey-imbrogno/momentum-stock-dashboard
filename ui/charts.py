from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from scanner.indicators import add_indicators
from scanner.models import StockAnalysis


RANGE_TO_SESSIONS = {
    "3M": 63,
    "6M": 126,
    "1Y": 252,
    "2Y": 504,
}


def make_stock_chart(analysis: StockAnalysis, range_label: str = "6M") -> go.Figure:
    history = analysis.history
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.72, 0.28],
        vertical_spacing=0.04,
    )
    if history is None or history.empty:
        fig.update_layout(height=560, template="plotly_white", annotations=[{"text": "No chart data available.", "showarrow": False}])
        return fig

    sessions = RANGE_TO_SESSIONS.get(range_label, 126)
    df = add_indicators(history).tail(sessions)
    x = df.index

    fig.add_trace(
        go.Candlestick(
            x=x,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
            increasing_line_color="#147d4f",
            decreasing_line_color="#b42318",
        ),
        row=1,
        col=1,
    )

    moving_averages = {
        "10 EMA": ("EMA10", "#4c78a8"),
        "21 EMA": ("EMA21", "#f58518"),
        "50 SMA": ("SMA50", "#54a24b"),
        "150 SMA": ("SMA150", "#b279a2"),
        "200 SMA": ("SMA200", "#79706e"),
    }
    for name, (column, color) in moving_averages.items():
        fig.add_trace(
            go.Scatter(x=x, y=df[column], name=name, line={"width": 1.4, "color": color}),
            row=1,
            col=1,
        )

    volume_colors = ["#147d4f" if close >= open_ else "#b42318" for open_, close in zip(df["Open"], df["Close"])]
    fig.add_trace(
        go.Bar(x=x, y=df["Volume"], name="Volume", marker_color=volume_colors, opacity=0.65),
        row=2,
        col=1,
    )

    levels = {
        "Pivot": analysis.pivot.pivot,
        "Entry": analysis.pivot.entry,
        "Stop": analysis.stop_plan.stop,
        "2R": analysis.stop_plan.target_2r,
        "3R": analysis.stop_plan.target_3r,
    }
    colors = {
        "Pivot": "#344054",
        "Entry": "#147d4f",
        "Stop": "#b42318",
        "2R": "#7a5af8",
        "3R": "#6941c6",
    }
    for label, value in levels.items():
        if value is None or pd.isna(value):
            continue
        fig.add_hline(
            y=value,
            line_dash="dot",
            line_color=colors[label],
            annotation_text=label,
            annotation_position="right",
            row=1,
            col=1,
        )

    fig.update_layout(
        height=610,
        template="plotly_white",
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
        xaxis_rangeslider_visible=False,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    return fig
