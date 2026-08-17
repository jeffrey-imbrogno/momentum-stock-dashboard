from __future__ import annotations

import pandas as pd

from config import ScannerConfig
from data.cache import load_universe


def get_universe(config: ScannerConfig) -> pd.DataFrame:
    return load_universe(config.universe_path)


def apply_universe_filters(universe: pd.DataFrame) -> pd.DataFrame:
    df = universe.copy()
    blocked_tokens = ("ETF", "WARRANT", "RIGHT", "UNIT", "PREFERRED")
    text = (
        df["company"].fillna("").str.upper()
        + " "
        + df["industry"].fillna("").str.upper()
        + " "
        + df["exchange"].fillna("").str.upper()
    )
    mask = ~text.str.contains("|".join(blocked_tokens), regex=True)
    mask &= ~df["exchange"].fillna("").str.upper().eq("OTC")
    return df[mask].reset_index(drop=True)
