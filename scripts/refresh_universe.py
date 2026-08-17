from __future__ import annotations

from pathlib import Path

import pandas as pd


NASDAQ_LISTED = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
OUTPUT = Path("data/us_stock_universe.csv")


def _read_pipe_file(url: str) -> pd.DataFrame:
    frame = pd.read_csv(url, sep="|")
    frame = frame[~frame.iloc[:, 0].astype(str).str.contains("File Creation Time", na=False)]
    return frame


def main() -> None:
    nasdaq = _read_pipe_file(NASDAQ_LISTED)
    other = _read_pipe_file(OTHER_LISTED)

    nasdaq = nasdaq.rename(columns={"Symbol": "ticker", "Security Name": "company"})
    nasdaq["exchange"] = "NASDAQ"

    other = other.rename(columns={"ACT Symbol": "ticker", "Security Name": "company", "Exchange": "exchange"})
    exchanges = {"N": "NYSE", "A": "NYSE American", "P": "NYSE Arca", "Z": "Cboe BZX", "V": "IEX"}
    other["exchange"] = other["exchange"].map(exchanges).fillna(other["exchange"])

    combined = pd.concat(
        [
            nasdaq[["ticker", "company", "exchange"]],
            other[["ticker", "company", "exchange"]],
        ],
        ignore_index=True,
    )
    combined["ticker"] = combined["ticker"].astype(str).str.upper().str.strip()
    combined["company"] = combined["company"].astype(str).str.strip()
    text = combined["ticker"] + " " + combined["company"].str.upper()
    exclude = r"\$|ETF|ETN|WARRANT|RIGHT|UNIT|PREFERRED|PFD|TEST STOCK"
    combined = combined[~text.str.contains(exclude, regex=True, na=False)].copy()
    combined = combined[combined["ticker"].str.fullmatch(r"[A-Z]{1,5}", na=False)]
    combined["sector"] = ""
    combined["industry"] = ""
    combined = combined.drop_duplicates(subset=["ticker"]).sort_values("ticker")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    combined[["ticker", "company", "exchange", "sector", "industry"]].to_csv(OUTPUT, index=False)
    print(f"Wrote {len(combined):,} symbols to {OUTPUT}")


if __name__ == "__main__":
    main()
