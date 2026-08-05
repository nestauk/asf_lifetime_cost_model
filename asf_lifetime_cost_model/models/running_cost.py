"""Running (fuel) cost calculations for a HeatingSystem.

Split out of heating_system.py to keep HeatingSystem's core construction and
discounting logic readable. RunningCostMixin is mixed into HeatingSystem, so
these remain instance methods (self is a HeatingSystem) with access to its
attributes (efficiency, operating_years, ...), validators, and
_discount_factor/_annuity_factor/_resolve_discount_base_year/_annualise
helpers.
"""

from typing import TYPE_CHECKING, Optional

from asf_lifetime_cost_model import config
from asf_lifetime_cost_model.models.trajectory import EnergyPriceTrajectory

if TYPE_CHECKING:
    from asf_lifetime_cost_model.models.heating_system import HeatingSystem

DEFAULT_DISCOUNT_RATE = config["default_discount_rate"]


class RunningCostMixin:
    """Adds running (fuel) cost calculations to HeatingSystem."""

    def calculate_energy_demand(self: "HeatingSystem", heat_demand: float) -> float:
        """Fuel input needed to meet a given heat demand, based on this system's fixed efficiency.

        Heat demand in kWh/year.
        """
        return heat_demand / self.efficiency

    def calculate_running_cost(
        self: "HeatingSystem",
        year: int,
        heat_demand: float,
        energy_price_trajectory: EnergyPriceTrajectory,
        standing_charge: float = 0.0,  # p/day, real terms. Flat for now; may become a trajectory later.
    ) -> float:
        """Running cost (undiscounted) for a single year = energy demand x fuel price that year.

        Converted to £, plus standing_charge (p/day, converted to £/year: standing_charge / 100 * 365).

        energy_price_trajectory prices are in p/kWh; this converts to £ so
        the result can be summed with installation_cost/subsidy/maintenance,
        which are all in £.

        Raises if year is outside this system's operating_years.
        Heat demand in kWh/year.
        """
        self._validate_year_in_operating_years(year=year)
        self._validate_energy_price_trajectory(energy_price_trajectory=energy_price_trajectory)
        energy_demand = self.calculate_energy_demand(heat_demand=heat_demand)
        price_in_pounds = energy_price_trajectory.get_price(year=year) / 100  # p/kWh -> £/kWh
        annual_variable_cost = energy_demand * price_in_pounds
        annual_standing_charge_in_pounds = standing_charge / 100 * 365  # p/day -> £/year
        return annual_variable_cost + annual_standing_charge_in_pounds

    def calculate_lifetime_running_cost(
        self: "HeatingSystem",
        heat_demand: float,
        energy_price_trajectory: EnergyPriceTrajectory,
        standing_charge: float = 0.0,  # p/day, real terms. Flat for now; may become a trajectory later.
    ) -> float:
        """Total (undiscounted) running cost (£) summed across every year of operation, in real terms.

        Heat demand in kWh/year.
        """
        return sum(
            self.calculate_running_cost(
                year=year,
                heat_demand=heat_demand,
                energy_price_trajectory=energy_price_trajectory,
                standing_charge=standing_charge,
            )
            for year in self.operating_years
        )

    def calculate_discounted_running_cost(
        self: "HeatingSystem",
        year: int,
        heat_demand: float,
        energy_price_trajectory: EnergyPriceTrajectory,
        standing_charge: float = 0.0,  # p/day, real terms. Flat for now; may become a trajectory later.
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        discount_base_year: Optional[int] = None,
    ) -> float:
        """Running cost for a single year, discounted back to discount_base_year.

        Raises if year is outside this system's operating_years.
        Heat demand in kWh/year.
        """
        self._validate_year_in_operating_years(year=year)
        discount_base_year = self._resolve_discount_base_year(discount_base_year)
        running_cost = self.calculate_running_cost(
            year=year,
            heat_demand=heat_demand,
            energy_price_trajectory=energy_price_trajectory,
            standing_charge=standing_charge,
        )
        return running_cost * self._discount_factor(
            year=year, discount_base_year=discount_base_year, discount_rate=discount_rate
        )

    def calculate_discounted_lifetime_running_cost(
        self: "HeatingSystem",
        heat_demand: float,
        energy_price_trajectory: EnergyPriceTrajectory,
        standing_charge: float = 0.0,  # p/day, real terms. Flat for now; may become a trajectory later.
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        discount_base_year: Optional[int] = None,
    ) -> float:
        """Total running cost summed across every year of operation, each year discounted back to discount_base_year.

        Heat demand in kWh/year.
        """
        discount_base_year = self._resolve_discount_base_year(discount_base_year)
        return sum(
            self.calculate_discounted_running_cost(
                year=year,
                heat_demand=heat_demand,
                energy_price_trajectory=energy_price_trajectory,
                standing_charge=standing_charge,
                discount_rate=discount_rate,
                discount_base_year=discount_base_year,
            )
            for year in self.operating_years
        )

    def calculate_annualised_discounted_lifetime_running_cost(
        self: "HeatingSystem",
        heat_demand: float,
        energy_price_trajectory: EnergyPriceTrajectory,
        standing_charge: float = 0.0,
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        discount_base_year: Optional[int] = None,
    ) -> float:
        """Equivalent Annual Cost of just the running cost component."""
        npv = self.calculate_discounted_lifetime_running_cost(
            heat_demand=heat_demand,
            energy_price_trajectory=energy_price_trajectory,
            standing_charge=standing_charge,
            discount_rate=discount_rate,
            discount_base_year=discount_base_year,
        )
        return self._annualise(npv, discount_rate=discount_rate)
