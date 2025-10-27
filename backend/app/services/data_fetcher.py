"""Utility functions for fetching price data used across tests and services."""
from __future__ import annotations

from typing import Optional

import pandas as pd

from .indicators import load_sample_data


def get_stock_data(
    symbol: str,
    start_date: str,
    end_date: str,
    *,
    include_indicators: bool = False,
) -> pd.DataFrame:
    """Load OHLCV data for the given symbol and date range.

    Args:
        symbol: Ticker symbol such as "AAPL" or "005930".
        start_date: Inclusive start date (YYYY-MM-DD).
        end_date: Exclusive end date (YYYY-MM-DD).
        include_indicators: When True, keep indicator columns computed by
            ``load_sample_data``. Otherwise only OHLCV columns are returned.

    Returns:
        Pandas DataFrame containing at least ``open``, ``high``, ``low``,
        ``close`` and ``volume`` columns.
    """
    df = load_sample_data(symbol, start_date, end_date)
    if df is None or df.empty:
        raise ValueError(
            f"No price data available for {symbol} in {start_date}~{end_date}."
        )

    if include_indicators:
        return df

    base_cols = [col for col in ("open", "high", "low", "close", "volume") if col in df.columns]
    if not base_cols:
        raise ValueError("Expected OHLCV columns were not found in the dataset.")

    return df[base_cols].copy()
