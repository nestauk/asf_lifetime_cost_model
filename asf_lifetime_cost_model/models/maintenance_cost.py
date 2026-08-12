"""Maintenance cost calculations for a HeatingSystem.

Split out of heating_system.py to keep HeatingSystem's core construction and
discounting logic readable. MaintenanceCostMixin is mixed into HeatingSystem,
so these remain instance methods (self is a HeatingSystem) with access to its
attributes (maintenance_cost_per_visit, maintenance_annual_frequency, ...),
validators, and _discount_factor/_annuity_factor/_resolve_discount_base_year/
_annualise helpers.
"""

from typing import TYPE_CHECKING, Optional

from asf_lifetime_cost_model import config

if TYPE_CHECKING:
    from asf_lifetime_cost_model.models.heating_system import HeatingSystem

DEFAULT_DISCOUNT_RATE = config["default_discount_rate"]


class MaintenanceCostMixin:
    """Adds maintenance cost calculations to HeatingSystem."""

    def calculate_annual_maintenance_cost(self: "HeatingSystem") -> float:
        """Expected annual maintenance cost, undiscounted, real terms.

        E.g. cost_per_visit=100, frequency=0.5 -> £50/year average.
        """
        return self.maintenance_cost_per_visit * self.maintenance_annual_frequency

    def calculate_maintenance_cost_for_year(self: "HeatingSystem", year: int) -> float:
        """Maintenance cost for a specific year, undiscounted, real terms.

        Returns 0.0 for the installation year itself (new systems are
        typically still under warranty, with no maintenance cost yet).
        Raises if year is outside this system's operating_years.
        """
        self._validate_year_in_operating_years(year=year)
        if year == self.installation_year:
            return 0.0
        return self.calculate_annual_maintenance_cost()

    def calculate_lifetime_maintenance_cost(self: "HeatingSystem") -> float:
        """Total (undiscounted) maintenance cost summed across every year of operation, real terms.

        Excludes the installation year (assumed no maintenance cost).
        """
        return self.calculate_annual_maintenance_cost() * (len(self.operating_years) - 1)

    def calculate_discounted_maintenance_cost(
        self: "HeatingSystem",
        year: int,
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        discount_base_year: Optional[int] = None,
    ) -> float:
        """Maintenance cost for a single year, discounted back to discount_base_year.

        Returns zero for the installation year.
        Raises if year is outside this system's operating_years.
        """
        self._validate_year_in_operating_years(year=year)
        discount_base_year = self._resolve_discount_base_year(discount_base_year)
        maintenance_cost = self.calculate_maintenance_cost_for_year(year=year)
        return maintenance_cost * self._discount_factor(
            year=year, discount_base_year=discount_base_year, discount_rate=discount_rate
        )

    def calculate_discounted_lifetime_maintenance_cost(
        self: "HeatingSystem",
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        discount_base_year: Optional[int] = None,
    ) -> float:
        """Total maintenance cost summed across every year of operation, with present-value discounting.

        Each year is discounted back to discount_base_year.
        """
        discount_base_year = self._resolve_discount_base_year(discount_base_year)
        return sum(
            self.calculate_discounted_maintenance_cost(
                year=year, discount_rate=discount_rate, discount_base_year=discount_base_year
            )
            for year in self.operating_years
        )

    def calculate_annualised_discounted_lifetime_maintenance_cost(
        self: "HeatingSystem",
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        discount_base_year: Optional[int] = None,
    ) -> float:
        """Equivalent Annual Cost of just the maintenance cost component."""
        npv = self.calculate_discounted_lifetime_maintenance_cost(
            discount_rate=discount_rate, discount_base_year=discount_base_year
        )
        return self._annualise(npv, discount_rate=discount_rate)
