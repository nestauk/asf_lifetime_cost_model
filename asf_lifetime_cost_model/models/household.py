"""Represents a household and provides convenience access to its heating system's costs."""

from typing import Optional

from asf_lifetime_cost_model import config
from asf_lifetime_cost_model.models.energy_price_trajectory import EnergyPriceTrajectory
from asf_lifetime_cost_model.models.heating_system import HeatingSystem

DEFAULT_DISCOUNT_RATE = config["default_discount_rate"]


class Household:
    """Represents a household with a heat demand and a heating system.

    Heat demand in kWh/year.
    """

    def __init__(self, name: str, heat_demand: float, heating_system: HeatingSystem) -> None:
        """Set up a household with a name, heat demand, and heating system."""
        self.name = name
        self.heat_demand = heat_demand
        self.heating_system = heating_system

    def get_upfront_cost(self) -> float:
        """Upfront cost (installation cost minus subsidy) of this household's heating system."""
        return self.heating_system.upfront_cost

    def get_maintenance_cost(self) -> float:
        """Expected annual maintenance cost of this household's heating system."""
        return self.heating_system.calculate_maintenance_cost()

    def get_annual_loan_repayment(self) -> float:
        """Equal annual loan repayment for this household's heating system, if financed via a loan."""
        return self.heating_system.calculate_annual_loan_repayment()

    def get_running_cost(self, year: int, energy_price_trajectory: EnergyPriceTrajectory) -> float:
        """Running cost of this household's heating system for a given year, in real terms.

        `energy_price_trajectory` must be in real terms, match the heating system's fuel
        (electricity or gas), and share the same base_year as the heating system's cost trajectories.
        """
        return self.heating_system.calculate_running_cost(
            year=year,
            heat_demand=self.heat_demand,
            energy_price_trajectory=energy_price_trajectory,
        )

    def get_lifetime_running_cost(self, energy_price_trajectory: EnergyPriceTrajectory) -> float:
        """Total (undiscounted, real-terms) running cost over the heating system's lifespan."""
        return self.heating_system.calculate_lifetime_running_cost(
            heat_demand=self.heat_demand,
            energy_price_trajectory=energy_price_trajectory,
        )

    def get_lifetime_cost(self, energy_price_trajectory: EnergyPriceTrajectory) -> float:
        """Total (undiscounted, real-terms) lifetime cost of this household's heating system.

        `energy_price_trajectory` must be in real terms and share the same base_year as
        the heating system's cost trajectories.
        """
        return self.heating_system.calculate_lifetime_cost(
            heat_demand=self.heat_demand,
            energy_price_trajectory=energy_price_trajectory,
        )

    def get_annualised_lifetime_cost(self, energy_price_trajectory: EnergyPriceTrajectory) -> float:
        """Annualised (undiscounted, real-terms) lifetime cost of this household's heating system.

        `energy_price_trajectory` must be in real terms and share the same base_year as
        the heating system's cost trajectories.
        """
        return self.heating_system.calculate_annualised_lifetime_cost(
            heat_demand=self.heat_demand,
            energy_price_trajectory=energy_price_trajectory,
        )

    def get_discounted_lifetime_cost(
        self,
        energy_price_trajectory: EnergyPriceTrajectory,
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        discount_base_year: Optional[int] = None,
    ) -> float:
        """Present-value lifetime cost of this household's heating system.

        Discounted back to discount_base_year (defaults to the heating
        system's own installation_year). Passing a single shared
        discount_base_year lets you compare households/systems installed in
        different years on a like-for-like basis.

        `energy_price_trajectory` must be in real terms and share the same
        base_year as the heating system's cost trajectories.
        """
        return self.heating_system.calculate_discounted_lifetime_cost(
            heat_demand=self.heat_demand,
            energy_price_trajectory=energy_price_trajectory,
            discount_rate=discount_rate,
            discount_base_year=discount_base_year,
        )

    def get_annualised_discounted_lifetime_cost(
        self,
        energy_price_trajectory: EnergyPriceTrajectory,
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        discount_base_year: Optional[int] = None,
    ) -> float:
        """Equivalent Annual Cost (EAC) of this household's heating system.

        See HeatingSystem.calculate_annualised_discounted_lifetime_cost for details.
        """
        return self.heating_system.calculate_annualised_discounted_lifetime_cost(
            heat_demand=self.heat_demand,
            energy_price_trajectory=energy_price_trajectory,
            discount_rate=discount_rate,
            discount_base_year=discount_base_year,
        )

    def __repr__(self) -> str:
        """Return a string representation showing the household's name, heat demand, and heating system."""
        return f"Household(name={self.name!r}, heat_demand={self.heat_demand}, heating_system={self.heating_system})"
