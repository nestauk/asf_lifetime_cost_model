"""Object holding installation costs for each year in 2026-2035 for a named heating system type."""

from typing import Callable, Dict, Union

import numpy as np
import pandas as pd

from asf_lifetime_cost_model import config


class InstallationCostTrajectory:
    """Holds an installation cost trajectory (2026-2035) for a heating system.

    Heating system types cover e.g. 'air_to_water_heat_pump', 'gas_boiler').
    Costs are in £.
    """

    INSTALL_YEARS = pd.RangeIndex(config["install_start_year"], config["install_end_year"] + 1, name="year")
    UNIT = config["currency_unit"]

    def __init__(self, system_type: str, starting_cost: float) -> None:
        """Instantiate trajectory with a starting cost, flat across all years."""
        self.system_type = system_type
        self.cost = pd.Series(starting_cost, index=self.INSTALL_YEARS, dtype=float)

    def set_trajectory(
        self, values: Union[float, Dict[int, float], Callable[[int], float]], from_year: int = 2027
    ) -> None:
        """Update the cost trajectory from `from_year` onwards.

        - float: treated as a constant annual growth rate (e.g. 0.02 for 2%)
        - dict: explicit {year: cost} overrides
        - callable: fn(year) -> cost, applied to each year from `from_year`
        """
        min_year, max_year = self.INSTALL_YEARS.min(), self.INSTALL_YEARS.max()

        if isinstance(values, dict):
            invalid_years = [year for year in values if year not in self.cost.index]
            if invalid_years:
                raise ValueError(f"Years {invalid_years} outside valid range ({min_year}-{max_year})")
            for year, value in values.items():
                self.cost.loc[year] = value
        elif callable(values):
            if not (min_year <= from_year <= max_year):
                raise ValueError(f"from_year {from_year} outside valid range ({min_year}-{max_year})")
            for year in self.cost.loc[from_year:].index:
                self.cost.loc[year] = values(year)
        else:  # float growth rate
            if not (min_year < from_year <= max_year):
                raise ValueError(f"from_year {from_year} must be between {min_year + 1} and {max_year}")
            years_to_update = self.cost.loc[from_year:].index
            n = len(years_to_update)
            base_value = self.cost.loc[from_year - 1]
            self.cost.loc[from_year:] = base_value * (1 + values) ** np.arange(1, n + 1)

    def get_cost(self, year: int) -> float:
        """Return installation cost for a given year."""
        return self.cost.loc[year]

    def __repr__(self) -> str:
        """Return a string representation showing the system type, unit, and full cost trajectory."""
        cost_str = ", ".join(f"{year}: {cost:.2f}" for year, cost in self.cost.items())
        return f"InstallationCostTrajectory(system_type={self.system_type!r}, unit={self.UNIT!r}, cost={{{cost_str}}})"
