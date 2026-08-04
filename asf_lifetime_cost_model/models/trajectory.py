from typing import Callable, Dict, Union

import numpy as np
import pandas as pd

from asf_lifetime_cost_model import config
from asf_lifetime_cost_model.utils.utils import deflate_series, inflate_series

INSTALL_YEARS = pd.RangeIndex(config["install_start_year"], config["install_end_year"] + 1, name="year")
OPERATING_YEARS = pd.RangeIndex(config["operating_start_year"], config["operating_end_year"] + 1, name="year")


class BaseTrajectory:
    """Base class for year-indexed numeric trajectories."""

    UNIT: str = ""

    def __init__(
        self,
        identifier_name: str,
        identifier_value: str,
        starting_value: float,
        years_index: pd.Index,
        price_basis: str = "nominal",
        base_year: int | None = None,
    ) -> None:
        """Flexible template class for specific types of trajectory.

        identifier_name: Sub-class specific attribute name (e.g. system type, fuel).
        identifier_value: Sub-class specific attribute value.
        starting_value: initial trajectory value.
        years_index: pandas index of years to consider.
        price_basis: "nominal" (default) if starting_subsidy is today's actual
        cash figure, or "real" if starting_subsidy is already expressed in a
        fixed base_year's purchasing power (base_year must be given if so).
        base_year: year requried for price_basis = 'real'.
        """
        if price_basis == "real" and base_year is None:
            raise ValueError("base_year must be provided when price_basis='real'")

        self._identifier_name = identifier_name
        self._identifier_value = identifier_value
        setattr(self, identifier_name, identifier_value)

        self.series = pd.Series(starting_value, index=years_index, dtype=float)
        self.price_basis = price_basis
        self.base_year = base_year

    def set_trajectory(
        self, values: Union[float, Dict[int, float], Callable[[int], float]], from_year: int = 2027
    ) -> None:
        """Update the trajectory from `from_year` onwards."""
        min_year, max_year = self.series.index.min(), self.series.index.max()

        if isinstance(values, dict):
            invalid_years = [y for y in values if y not in self.series.index]
            if invalid_years:
                raise ValueError(f"Years {invalid_years} outside valid range ({min_year}-{max_year})")
            for year, val in values.items():
                self.series.loc[year] = val
        elif callable(values):
            if not (min_year <= from_year <= max_year):
                raise ValueError(f"from_year {from_year} outside valid range ({min_year}-{max_year})")
            for year in self.series.loc[from_year:].index:
                self.series.loc[year] = values(year)
        else:  # float growth rate
            if not (min_year < from_year <= max_year):
                raise ValueError(f"from_year {from_year} must be between {min_year + 1} and {max_year}")
            years_to_update = self.series.loc[from_year:].index
            n = len(years_to_update)
            base_value = self.series.loc[from_year - 1]
            self.series.loc[from_year:] = base_value * (1 + values) ** np.arange(1, n + 1)

    def get_value(self, year: int) -> float:
        """Return trajectory value for a given year."""
        return self.series.loc[year]

    def to_real(self, base_year: int, inflation_rate: float) -> None:
        """Deflate this trajectory's values from nominal to base_year real terms, in place.

        Raises if already real.
        """
        if self.price_basis == "real":
            raise ValueError(f"Already in real terms (base_year={self.base_year}); would double-deflate.")
        self.series = deflate_series(self.series, base_year, inflation_rate)
        self.price_basis = "real"
        self.base_year = base_year

    def to_nominal(self, inflation_rate: float) -> None:
        """Inflate values from real to nominal terms in place."""
        if self.price_basis == "nominal":
            raise ValueError("Already in nominal terms; would double-inflate.")
        self.series = inflate_series(self.series, self.base_year, inflation_rate)
        self.price_basis = "nominal"
        self.base_year = None

    def as_series(self) -> pd.Series:
        """Return a copy of the underlying year-indexed pd.Series."""
        return self.series.copy()

    def __repr__(self) -> str:
        """Return a string representation of the trajectory."""
        vals_str = ", ".join(f"{year}: {val:.2f}" for year, val in self.series.items())
        basis_str = (
            f"{self.price_basis!r} (base_year={self.base_year})"
            if self.price_basis == "real"
            else repr(self.price_basis)
        )
        return (
            f"{self.__class__.__name__}({self._identifier_name}={self._identifier_value!r}, "
            f"unit={self.UNIT!r}, price_basis={basis_str}, {self.VALUES_LABEL}={{{vals_str}}})"
        )


class SubsidyTrajectory(BaseTrajectory):
    """Holds a subsidy trajectory (2026-2035) for a heating system.

    Heating system types cover e.g. 'air_to_water_heat_pump', 'gas_boiler').
    Costs are in £. Tracks whether values are currently in nominal (actual
    cash) or real (base-year) terms via price_basis, to guard against
    accidental double-conversion.
    """

    UNIT = config["currency_unit"]
    VALUES_LABEL = "subsidy"

    def __init__(
        self, system_type: str, starting_subsidy: float, price_basis: str = "nominal", base_year: int | None = None
    ) -> None:
        """Instantiate trajectory with a starting value, flat across all years.

        price_basis: "nominal" (default) if starting_subsidy is today's actual
        cash figure, or "real" if starting_subsidy is already expressed in a
        fixed base_year's purchasing power (base_year must be given if so).
        """
        super().__init__("system_type", system_type, starting_subsidy, INSTALL_YEARS, price_basis, base_year)

    @property
    def subsidy(self) -> pd.Series:
        """Named subsidy field from generic series attribute."""
        return self.series

    def get_subsidy(self, year: int) -> float:
        """Return subsidy value for a given year."""
        return self.get_value(year)


class InstallationCostTrajectory(BaseTrajectory):
    """Holds an installation cost trajectory (2026-2035) for a heating system.

    Heating system types cover e.g. 'air_to_water_heat_pump', 'gas_boiler').
    Costs are in £. Tracks whether values are currently in nominal (actual
    cash) or real (base-year) terms via price_basis, to guard against
    accidental double-conversion.
    """

    UNIT = config["currency_unit"]
    VALUES_LABEL = "installation_cost"

    def __init__(
        self, system_type: str, starting_cost: float, price_basis: str = "nominal", base_year: int | None = None
    ) -> None:
        """Instantiate trajectory with a starting cost, flat across all years.

        price_basis: "nominal" (default) if starting_cost is today's actual
        cash figure, or "real" if starting_cost is already expressed in a
        fixed base_year's purchasing power (base_year must be given if so).
        """
        super().__init__("system_type", system_type, starting_cost, INSTALL_YEARS, price_basis, base_year)

    @property
    def cost(self) -> pd.Series:
        """Named cost field from generic series attribute."""
        return self.series

    def get_cost(self, year: int) -> float:
        """Return installation cost for a given year."""
        return self.get_value(year)


class EnergyPriceTrajectory(BaseTrajectory):
    """Holds a price trajectory (2026-2050) for a single fuel type.

    Covers a single fuel type (e.g. 'electricity' or 'gas'). Prices are in
    p/kWh (pence per kilowatt-hour). Tracks whether values are currently in
    nominal (actual cash) or real (base-year) terms via price_basis, to
    guard against accidental double-conversion.
    """

    UNIT = config["energy_price_unit"]
    VALUES_LABEL = "prices"

    def __init__(
        self, fuel: str, starting_price: float, price_basis: str = "nominal", base_year: int | None = None
    ) -> None:
        """Seed the trajectory with a starting price, flat across all years.

        price_basis: "nominal" (default) if starting_price is today's actual
        cash figure, or "real" if starting_price is already expressed in a
        fixed base_year's purchasing power (base_year must be given if so).
        """
        super().__init__("fuel", fuel, starting_price, OPERATING_YEARS, price_basis, base_year)

    @property
    def prices(self) -> pd.Series:
        """Named prices field from generic series attribute."""
        return self.series

    def get_price(self, year: int) -> float:
        """Return the price for a given year."""
        return self.get_value(year)

    def apply_percentage_discount(self, discount_rate: float) -> None:
        """Apply a flat percentage discount to every year's price, in place.

        E.g. discount_rate=0.15 reduces every year's price by 15%
        (representing a time-of-use tariff discount on the unit rate).
        """
        self.series = self.series * (1 - discount_rate)
