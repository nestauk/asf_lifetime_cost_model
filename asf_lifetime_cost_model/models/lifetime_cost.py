"""Total and annualised lifetime cost calculations for a HeatingSystem.

Split out of heating_system.py to keep HeatingSystem's core construction and
discounting logic readable. LifetimeCostMixin is mixed into HeatingSystem, so
these remain instance methods (self is a HeatingSystem) that combine the
running, capital, and maintenance cost mixins' calculations, plus
_annualise/_resolve_discount_base_year helpers.
"""

from typing import TYPE_CHECKING, Optional

from asf_lifetime_cost_model import config
from asf_lifetime_cost_model.models.trajectory import EnergyPriceTrajectory

if TYPE_CHECKING:
    from asf_lifetime_cost_model.models.heating_system import HeatingSystem

DEFAULT_DISCOUNT_RATE = config["default_discount_rate"]


class LifetimeCostMixin:
    """Adds total and annualised lifetime cost calculations to HeatingSystem."""

    def calculate_lifetime_cost(
        self: "HeatingSystem",
        heat_demand: float,
        energy_price_trajectory: EnergyPriceTrajectory,
        standing_charge: float = 0.0,  # p/day, real terms. Flat for now; may become a trajectory later.
    ) -> float:
        """Total (undiscounted, real-terms) cost over the system's lifespan.

        Includes running cost and maintenance cost summed across every year of operation,
        plus either the upfront cost paid once (unfinanced) or annual loan repayments summed
        over the loan term (financed). No time-value discounting applied — see
        calculate_discounted_lifetime_cost for present-value terms.

        Heat demand must be provided in kWh/year.
        """
        total_running_cost = self.calculate_lifetime_running_cost(
            heat_demand=heat_demand, energy_price_trajectory=energy_price_trajectory, standing_charge=standing_charge
        )
        total_maintenance_cost = self.calculate_lifetime_maintenance_cost()
        total_capital_cost = self.calculate_lifetime_capital_cost()

        return total_capital_cost + total_running_cost + total_maintenance_cost

    def calculate_discounted_lifetime_cost(
        self: "HeatingSystem",
        heat_demand: float,
        energy_price_trajectory: EnergyPriceTrajectory,
        standing_charge: float = 0.0,  # p/day, real terms. Flat for now; may become a trajectory later.
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        discount_base_year: Optional[int] = None,
    ) -> float:
        """Lifetime cost expressed in present-value terms.

        Built from calculate_discounted_lifetime_capital_cost, calculate_discounted_lifetime_maintenance_cost,
        and calculate_discounted_lifetime_running_cost, so the sum of those
        three individual methods always equals this total exactly.

        Heat demand in kWh/year.
        """
        discount_base_year = self._resolve_discount_base_year(discount_base_year)

        discounted_capital_cost = self.calculate_discounted_lifetime_capital_cost(
            discount_rate=discount_rate, discount_base_year=discount_base_year
        )
        discounted_maintenance_cost = self.calculate_discounted_lifetime_maintenance_cost(
            discount_rate=discount_rate, discount_base_year=discount_base_year
        )
        discounted_running_cost = self.calculate_discounted_lifetime_running_cost(
            heat_demand=heat_demand,
            energy_price_trajectory=energy_price_trajectory,
            standing_charge=standing_charge,
            discount_rate=discount_rate,
            discount_base_year=discount_base_year,
        )

        return discounted_capital_cost + discounted_maintenance_cost + discounted_running_cost

    def calculate_annualised_lifetime_cost(
        self: "HeatingSystem",
        heat_demand: float,
        energy_price_trajectory: EnergyPriceTrajectory,
        standing_charge: float = 0.0,  # p/day, real terms. Flat for now; may become a trajectory later.
    ) -> float:
        """Annualised (undiscounted, real-terms) total cost over the system's lifespan.

        Equals the lifetime cost (upfront/financing + running + maintenance) spread evenly across
        every year of operation.

        Heat demand must be provided in kWh/year.
        """
        total_lifetime_cost = self.calculate_lifetime_cost(
            heat_demand=heat_demand, energy_price_trajectory=energy_price_trajectory, standing_charge=standing_charge
        )
        return total_lifetime_cost / len(self.operating_years)

    def calculate_annualised_discounted_lifetime_cost(
        self: "HeatingSystem",
        heat_demand: float,
        energy_price_trajectory: EnergyPriceTrajectory,
        standing_charge: float = 0.0,
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        discount_base_year: Optional[int] = None,
    ) -> float:
        """Equivalent Annual Cost (EAC): a level annual amount, over the system's lifespan.

        Unlike calculate_annualised_lifetime_cost (which divides the
        undiscounted total by the number of years), this accounts for the
        fact that later years' costs are worth less today, using the
        annuity-due formula (see _annuity_factor): EAC = NPV * r / ((1 + r)
        * (1 - (1 + r) ** -n)). The annuity-due convention matches this
        model's discounting, where the first operating year (t=0) is
        undiscounted.

        Heat demand in kWh/year.
        """
        npv = self.calculate_discounted_lifetime_cost(
            heat_demand=heat_demand,
            energy_price_trajectory=energy_price_trajectory,
            standing_charge=standing_charge,
            discount_rate=discount_rate,
            discount_base_year=discount_base_year,
        )
        return self._annualise(npv, discount_rate=discount_rate)
