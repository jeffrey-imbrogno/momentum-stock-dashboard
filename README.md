# Momentum Stock Dashboard

A mobile-friendly Streamlit dashboard for momentum stock screening inspired by Minervini-style Trend Template, relative strength, and VCP/base analysis.

The app separates stocks into:

- `BUY NOW`: entry has triggered and quality filters pass.
- `WATCH`: high-quality setups that are not yet actionable.
- `SEARCH`: objective analysis for any ticker, including tickers outside the current scan.
- `MARKET`: market regime, breadth, exposure, and portfolio heat.

The scanner is intentionally conservative. It does not manufacture a trade simply because a ticker is searched.

## Installation

```bash
python -m venv .venv
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the dashboard:

```bash
streamlit run app.py
```

## Settings

Use the sidebar to change:

- Account size
- Risk per trade
- Maximum portfolio heat
- Maximum number of positions
- Scan limit
- Minimum BUY score
- Minimum Momentum RS
- Maximum stop %
- Earnings exclusion window

Default position sizing:

```text
Account size = $100,000
Risk/trade = 0.50%
Dollar risk = account size * risk %
Shares = dollar risk / (entry - stop)
```

Default portfolio heat:

```text
Maximum portfolio heat = 3%
Maximum positions = 8
```

## Universe

The MVP universe is loaded from:

```text
data/us_stock_universe.csv
```

Required columns:

```text
ticker,company,exchange,sector,industry
```

Add stocks by editing the CSV. The scanner excludes likely ETFs, warrants, preferreds, units, OTC listings, low-priced stocks, and illiquid symbols.

You can attempt to refresh a broader symbol universe from public NASDAQ Trader symbol directories:

```bash
python scripts/refresh_universe.py
```

Sector and industry data from that public source is incomplete, so the CSV keeps those fields editable.

## Scanner Methodology

### Trend Template

The Trend Template checks:

- Price above 50, 150, and 200 DMA
- 50 DMA above 150 DMA
- 150 DMA above 200 DMA
- 200 DMA rising
- Price at least 30% above the 52-week low
- Price within 25% of the 52-week high

### Momentum RS

Momentum RS is a custom 0-100 score based on relative performance versus SPY over approximately:

- 3 months: 40%
- 6 months: 30%
- 12 months: 30%

When scanning a universe, scores are ranked across the scanned symbols. It is not the proprietary IBD RS Rating.

### VCP/Base Quality

The VCP engine looks for:

- Progressively smaller contractions
- ATR compression
- Daily range compression
- Volume dry-up
- Declining selling volume
- Tight closes
- Price near highs
- Tightening around the 10/21 EMA

### Pivot Detection

The pivot engine attempts to identify:

- VCP Pivot
- Flat Base
- Cup With Handle
- High Tight Flag
- 21 EMA Pullback
- Post-Earnings Breakout

If no reliable base exists, the result is `NO VALID SETUP`.

### Status Engine

`BUY NOW` requires:

- Score >= 80
- Trend Template >= 7/8
- Momentum RS >= 80
- Valid setup
- Stop <= 8%
- No earnings hold
- Current price between entry and entry + 3%
- Market regime not RED

Other statuses include `ON DECK`, `BUILDING`, `EARLY BASE`, `EXTENDED`, `EARNINGS HOLD`, `TREND FAILURE`, `TRIGGERED - MARKET RISK`, `INSUFFICIENT DATA`, and `NO VALID SETUP`.

## Data Source Limitations

The first data provider is `yfinance`, which is useful for prototyping but can be delayed, incomplete, rate-limited, or occasionally unavailable. Earnings and fundamental fields may be missing. Missing fundamentals display as `N/A` and do not automatically eliminate otherwise exceptional technical setups.

The data-access layer lives in `data/cache.py`, so yfinance can later be replaced with Polygon, Alpaca, Tiingo, or another provider without rewriting the scanner.

## Tests

Tests use synthetic OHLCV data and do not depend on live Yahoo responses.

```bash
pytest
```

## Project Structure

```text
app.py
config.py

scanner/
    fundamentals.py
    indicators.py
    market_regime.py
    models.py
    pipeline.py
    pivots.py
    relative_strength.py
    scoring.py
    trade_planner.py
    trend_template.py
    universe.py
    vcp.py

data/
    cache.py
    us_stock_universe.csv

ui/
    charts.py
    components.py

scripts/
    refresh_universe.py

tests/
```
