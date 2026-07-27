"""Object that holds price trajectories (2026-2050) for a single fuel type (electricity or gas)."""

from typing import Callable, Dict, Union

import numpy as np
import pandas as pd

from asf_lifetime_cost_model import config
from asf_lifetime_cost_model.utils.utils import deflate_series, inflate_series

OPERATING_YEARS = pd.RangeIndex(config["operating_start_year"], config["operating_end_year"] + 1, name="year")


class EnergyPriceTrajectory:
    """Holds a price trajectory (2026-2050) for a single fuel type.

    Covers a single fuel type (e.g. 'electricity' or 'gas'). Prices are in
    p/kWh (pence per kilowatt-hour). Tracks whether values are currently in
    nominal (actual cash) or real (base-year) terms via price_basis, to
    guard against accidental double-conversion.
    """

    UNIT = config["energy_price_unit"]

    def __init__(
        self, fuel: str, starting_price: float, price_basis: str = "nominal", base_year: int | None = None
    ) -> None:
        """Seed the trajectory with a starting price, flat across all years.

        price_basis: "nominal" (default) if starting_price is today's actual
        cash figure, or "real" if starting_price is already expressed in a
        fixed base_year's purchasing power (base_year must be given if so).
        """
        if price_basis == "real" and base_year is None:
            raise ValueError("base_year must be provided when price_basis='real'")

        self.fuel = fuel
        self.prices = pd.Series(starting_price, index=OPERATING_YEARS, dtype=float)
        self.price_basis = price_basis
        self.base_year = base_year

    def set_trajectory(
        self, values: Union[float, Dict[int, float], Callable[[int], float]], from_year: int = 2027
    ) -> None:
        """Update the price trajectory from `from_year` onwards.

        - float: treated as a constant annual growth rate (e.g. 0.02 for 2%),
          applied in whatever basis (nominal/real) the trajectory is currently in
        - dict: explicit {year: price} overrides
        - callable: fn(year) -> price, applied to each year from `from_year`
        """
        if isinstance(values, dict):
            for year, price in values.items():
                self.prices.loc[year] = price
        elif callable(values):
            for year in self.prices.loc[from_year:].index:
                self.prices.loc[year] = values(year)
        else:  # float growth rate
            years_to_update = self.prices.loc[from_year:].index
            n = len(years_to_update)
            base_price = self.prices.loc[from_year - 1]
            self.prices.loc[from_year:] = base_price * (1 + values) ** np.arange(1, n + 1)

    def get_price(self, year: int) -> float:
        """Return the price for a given year."""
        return self.prices.loc[year]

    def to_real(self, base_year: int, inflation_rate: float) -> None:
        """Deflate this trajectory's values from nominal to base_year real terms, in place.

        Raises if already real.
        """
        if self.price_basis == "real":
            raise ValueError(f"Already in real terms (base_year={self.base_year}); would double-deflate.")
        self.prices = deflate_series(self.prices, base_year, inflation_rate)
        self.price_basis = "real"
        self.base_year = base_year

    def to_nominal(self, inflation_rate: float) -> None:
        """Inflate this trajectory's values from real to nominal terms, in place.

        Raises if already nominal.
        """
        if self.price_basis == "nominal":
            raise ValueError("Already in nominal terms; would double-inflate.")
        self.prices = inflate_series(self.prices, self.base_year, inflation_rate)
        self.price_basis = "nominal"
        self.base_year = None

    def as_series(self) -> pd.Series:
        """Return the full price trajectory as a year-indexed pd.Series."""
        return self.prices.copy()

    def __repr__(self) -> str:
        """Return a string representation showing the fuel, unit, price basis (and base year if real), and full price trajectory."""
        prices_str = ", ".join(f"{year}: {price:.2f}" for year, price in self.prices.items())
        basis_str = (
            f"{self.price_basis!r} (base_year={self.base_year})"
            if self.price_basis == "real"
            else repr(self.price_basis)
        )
        return (
            f"EnergyPriceTrajectory(fuel={self.fuel!r}, unit={self.UNIT!r}, "
            f"price_basis={basis_str}, prices={{{prices_str}}})"
        )
