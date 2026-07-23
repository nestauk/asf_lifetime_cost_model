"""Represents a household and provides convenience access to its heating system's costs."""

from asf_lifetime_cost_model.models.energy_price_trajectory import EnergyPriceTrajectory
from asf_lifetime_cost_model.models.heating_system import HeatingSystem


class Household:
    """Represents a household with a heat demand and a heating system. Heat demand in kWh/year."""

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

    def get_running_cost(self, year: int, energy_price_trajectory: EnergyPriceTrajectory) -> float:
        """Running cost of this household's heating system for a given year.

        `energy_price_trajectory` must match the heating system's fuel (electricity or gas).
        """
        return self.heating_system.calculate_running_cost(
            year=year,
            heat_demand=self.heat_demand,
            energy_price_trajectory=energy_price_trajectory,
        )

    def get_lifetime_running_cost(self, energy_price_trajectory: EnergyPriceTrajectory) -> float:
        """Total running cost (fuel only) over the heating system's lifespan."""
        return self.heating_system.calculate_lifetime_running_cost(
            heat_demand=self.heat_demand,
            energy_price_trajectory=energy_price_trajectory,
        )

    def get_lifetime_cost(self, energy_price_trajectory: EnergyPriceTrajectory) -> float:
        """Total lifetime cost (upfront + running + maintenance) of this household's heating system.

        `energy_price_trajectory` must match the heating system's fuel (electricity or gas).
        """
        return self.heating_system.calculate_lifetime_cost(
            heat_demand=self.heat_demand,
            energy_price_trajectory=energy_price_trajectory,
        )

    def get_annualised_lifetime_cost(self, energy_price_trajectory: EnergyPriceTrajectory) -> float:
        """Annualised lifetime cost of this household's heating system.

        `energy_price_trajectory` must match the heating system's fuel (electricity or gas).
        """
        return self.heating_system.calculate_annualised_lifetime_cost(
            heat_demand=self.heat_demand,
            energy_price_trajectory=energy_price_trajectory,
        )

    def __repr__(self) -> str:
        """Return a string representation showing the household's name, heat demand, and heating system."""
        return f"Household(name={self.name!r}, heat_demand={self.heat_demand}, heating_system={self.heating_system})"
