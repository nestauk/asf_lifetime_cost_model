"""Shared utility functions."""

import pandas as pd


def deflate_to_real(nominal_value: float, year: int, base_year: int, inflation_rate: float) -> float:
    """Convert a nominal (actual-£-in-that-year) value into base_year real terms."""
    return nominal_value / (1 + inflation_rate) ** (year - base_year)


def inflate_to_nominal(real_value: float, year: int, base_year: int, inflation_rate: float) -> float:
    """Convert a real (base_year-terms) value into that year's nominal (actual cash) terms."""
    return real_value * (1 + inflation_rate) ** (year - base_year)


def deflate_series(series: pd.Series, base_year: int, inflation_rate: float) -> pd.Series:
    """Deflate a year-indexed pd.Series of nominal values into base_year real terms."""
    return series.index.to_series().apply(
        lambda year: deflate_to_real(series.loc[year], year, base_year, inflation_rate)
    )


def inflate_series(series: pd.Series, base_year: int, inflation_rate: float) -> pd.Series:
    """Inflate a year-indexed pd.Series of base_year-real values into each year's nominal terms."""
    return series.index.to_series().apply(
        lambda year: inflate_to_nominal(series.loc[year], year, base_year, inflation_rate)
    )
