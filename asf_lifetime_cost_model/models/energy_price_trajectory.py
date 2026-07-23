"""Object that holds price trajectories (2026-2050) for a single fuel type (electricity or gas)."""

from typing import Callable, Dict, Union

import numpy as np
import pandas as pd

from asf_lifetime_cost_model import config

YEARS = pd.RangeIndex(config["operating_start_year"], config["operating_end_year"] + 1, name="year")


class EnergyPriceTrajectory:
    """Holds a price trajectory (2026-2050) for a single fuel type.

    Covers a single fuel type (e.g. 'electricity' or 'gas'). Prices are in
    p/kWh (pence per kilowatt-hour).
    """

    UNIT = config["energy_price_unit"]

    def __init__(self, fuel: str, starting_price: float) -> None:
        """Instantiate trajectory with a starting price, flat across all years."""
        self.fuel = fuel
        self.prices = pd.Series(starting_price, index=YEARS, dtype=float)

    def set_trajectory(
        self, values: Union[float, Dict[int, float], Callable[[int], float]], from_year: int = 2027
    ) -> None:
        """Update the price trajectory from `from_year` onwards.

        - float: treated as a constant annual growth rate (e.g. 0.02 for 2%)
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

    def __repr__(self) -> str:
        """Return a string representation showing the fuel, unit, and full price trajectory."""
        prices_str = ", ".join(f"{year}: {price:.2f}" for year, price in self.prices.items())
        return f"EnergyPriceTrajectory(fuel={self.fuel!r}, unit={self.UNIT!r}, prices={{{prices_str}}})"
