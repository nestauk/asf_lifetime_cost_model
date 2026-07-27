"""Object holding upfront cost subsidy values for each year in 2026-2035 for a named heating system type."""

from typing import Callable, Dict, Union

import numpy as np
import pandas as pd

from asf_lifetime_cost_model import config
from asf_lifetime_cost_model.utils.utils import deflate_series, inflate_series

INSTALL_YEARS = pd.RangeIndex(config["install_start_year"], config["install_end_year"] + 1, name="year")


class SubsidyTrajectory:
    """Holds a subsidy trajectory (2026-2035) for a heating system.

    Heating system types cover e.g. 'air_to_water_heat_pump', 'gas_boiler').
    Costs are in £. Tracks whether values are currently in nominal (actual
    cash) or real (base-year) terms via price_basis, to guard against
    accidental double-conversion.
    """

    UNIT = config["currency_unit"]

    def __init__(
        self, system_type: str, starting_subsidy: float, price_basis: str = "nominal", base_year: int | None = None
    ) -> None:
        """Instantiate trajectory with a starting value, flat across all years.

        price_basis: "nominal" (default) if starting_subsidy is today's actual
        cash figure, or "real" if starting_subsidy is already expressed in a
        fixed base_year's purchasing power (base_year must be given if so).
        """
        if price_basis == "real" and base_year is None:
            raise ValueError("base_year must be provided when price_basis='real'")

        self.system_type = system_type
        self.subsidy = pd.Series(starting_subsidy, index=INSTALL_YEARS, dtype=float)
        self.price_basis = price_basis
        self.base_year = base_year

    def set_trajectory(
        self, values: Union[float, Dict[int, float], Callable[[int], float]], from_year: int = 2027
    ) -> None:
        """Update the subsidy trajectory from `from_year` onwards.

        - float: treated as a constant annual growth rate (e.g. 0.02 for 2%)
        - dict: explicit {year: subsidy} overrides
        - callable: fn(year) -> subsidy, applied to each year from `from_year`
        """
        min_year, max_year = INSTALL_YEARS.min(), INSTALL_YEARS.max()

        if isinstance(values, dict):
            invalid_years = [year for year in values if year not in self.subsidy.index]
            if invalid_years:
                raise ValueError(f"Years {invalid_years} outside valid range ({min_year}-{max_year})")
            for year, value in values.items():
                self.subsidy.loc[year] = value
        elif callable(values):
            if not (min_year <= from_year <= max_year):
                raise ValueError(f"from_year {from_year} outside valid range ({min_year}-{max_year})")
            for year in self.subsidy.loc[from_year:].index:
                self.subsidy.loc[year] = values(year)
        else:  # float growth rate
            if not (min_year < from_year <= max_year):
                raise ValueError(f"from_year {from_year} must be between {min_year + 1} and {max_year}")
            years_to_update = self.subsidy.loc[from_year:].index
            n = len(years_to_update)
            base_value = self.subsidy.loc[from_year - 1]
            self.subsidy.loc[from_year:] = base_value * (1 + values) ** np.arange(1, n + 1)

    def get_subsidy(self, year: int) -> float:
        """Return subsidy value for a given year."""
        return self.subsidy.loc[year]

    def to_real(self, base_year: int, inflation_rate: float) -> None:
        """Deflate this trajectory's values from nominal to base_year real terms, in place.

        Raises if already real.
        """
        if self.price_basis == "real":
            raise ValueError(f"Already in real terms (base_year={self.base_year}); would double-deflate.")
        self.subsidy = deflate_series(self.subsidy, base_year, inflation_rate)
        self.price_basis = "real"
        self.base_year = base_year

    def to_nominal(self, inflation_rate: float) -> None:
        """Inflate this trajectory's values from real to nominal terms, in place.

        Raises if already nominal.
        """
        if self.price_basis == "nominal":
            raise ValueError("Already in nominal terms; would double-inflate.")
        self.subsidy = inflate_series(self.subsidy, self.base_year, inflation_rate)
        self.price_basis = "nominal"
        self.base_year = None

    def __repr__(self) -> str:
        """Return a string representation showing the system type, unit, price basis (and base year if real), and full subsidy trajectory."""
        subsidy_str = ", ".join(f"{year}: {subsidy:.2f}" for year, subsidy in self.subsidy.items())
        basis_str = (
            f"{self.price_basis!r} (base_year={self.base_year})"
            if self.price_basis == "real"
            else repr(self.price_basis)
        )
        return (
            f"SubsidyTrajectory(system_type={self.system_type!r}, unit={self.UNIT!r}, "
            f"price_basis={basis_str}, subsidy={{{subsidy_str}}})"
        )
