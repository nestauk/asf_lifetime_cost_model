"""Solvers for the subsidy or electricity price a HeatingSystem would need to reach cost parity.

Split out of heating_system.py to keep HeatingSystem's core cost calculations
readable. ParitySolverMixin is mixed into HeatingSystem, so these remain
instance methods (self is a HeatingSystem) with access to its cost
calculations, trajectories, and _annuity_factor/_discount_factor helpers.
"""

from typing import TYPE_CHECKING, Optional

from asf_lifetime_cost_model import config
from asf_lifetime_cost_model.models.trajectory import EnergyPriceTrajectory

if TYPE_CHECKING:
    from asf_lifetime_cost_model.models.heating_system import HeatingSystem

DEFAULT_DISCOUNT_RATE = config["default_discount_rate"]


class ParitySolverMixin:
    """Adds solve_subsidy_for_parity and solve_electricity_price_for_parity to HeatingSystem."""

    def solve_subsidy_for_parity(
        self: "HeatingSystem",
        heat_demand: float,
        energy_price_trajectory: EnergyPriceTrajectory,
        target_eac: float,
        standing_charge: float = 0.0,
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        discount_base_year: Optional[int] = None,
    ) -> float:
        """Solve for the subsidy (£) this system would need for its Equivalent Annual Cost to equal target_eac.

        All other attributes (installation_cost, efficiency, financing, maintenance,
        etc.) are held exactly as already set on this HeatingSystem instance.
        Only subsidy is solved for, for this system's own installation_year.

        Heat demand in kWh/year. Returns the required subsidy in £.

        A negative result means this system is already cheaper than target_eac
        with zero subsidy so no subsidy is needed. You should should treat
        the result as £0 for display purposes rather than a literal negative
        subsidy. A result exceeding installation_cost means subsidy alone
        cannot close the gap (target_eac is unreachable via subsidy, even if
        the full installation cost were covered).
        """
        discount_base_year = self._resolve_discount_base_year(discount_base_year)

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

        annuity_factor = self._annuity_factor(discount_rate=discount_rate, n=self.lifespan)

        # how much of the target EAC is "used up" by maintenance and running costs
        eac_from_maintenance_and_running = annuity_factor * (discounted_maintenance_cost + discounted_running_cost)
        eac_budget_for_capital = target_eac - eac_from_maintenance_and_running

        # how much EAC does £1 of upfront cost actually cost with financing and discounting
        if self.is_financed:
            r = self.interest_rate
            n = self.loan_term
            annual_repayment_per_pound = 1 / n if r == 0 else r / (1 - (1 + r) ** -n)
            repayment_years = range(self.installation_year + 1, self.installation_year + self.loan_term + 1)
            discounted_capital_cost_per_pound = sum(
                annual_repayment_per_pound
                * self._discount_factor(year=year, discount_base_year=discount_base_year, discount_rate=discount_rate)
                for year in repayment_years
            )
        else:
            discounted_capital_cost_per_pound = self._discount_factor(
                year=self.installation_year, discount_base_year=discount_base_year, discount_rate=discount_rate
            )
        eac_per_pound_of_upfront_cost = annuity_factor * discounted_capital_cost_per_pound

        # required upfront cost to meet target EAC
        required_upfront_cost = eac_budget_for_capital / eac_per_pound_of_upfront_cost

        # calculate required subsidy gap to plug difference between install cost and required upfront cost
        required_subsidy = self.installation_cost - required_upfront_cost

        return required_subsidy

    def solve_electricity_price_for_parity(
        self: "HeatingSystem",
        heat_demand: float,
        energy_price_trajectory: EnergyPriceTrajectory,
        target_eac: float,
        standing_charge: float = 0.0,
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        discount_base_year: Optional[int] = None,
    ) -> dict:
        """Solve for the electricity prices needed for its Equivalent Annual Cost to equal target_eac.

        Scales energy_price_trajectory's existing year-to-year shape by a single multiplier.
        Standing_charge is held fixed (not scaled). Capital and maintenance costs are unaffected.

        Returns a dict of {year: solved_price}, in the same units as
        energy_price_trajectory (p/kWh), covering every year in operating_years.

        Two cases worth checking before interpreting the result:
        - If this system's EAC at the current electricity price is already below
            target_eac, the solved price represents how far electricity could
            rise before parity is lost — not a price that must be reached, since
            the system is already cheaper.
        - A negative scale factor (and therefore negative solved prices) means
            target_eac is unreachable: this system's capital, maintenance, and
            standing charge costs alone already exceed target_eac, even before
            any electricity cost is added, so no electricity price — including
            zero — could bring the system down to the target.
        """
        discount_base_year = self._resolve_discount_base_year(discount_base_year)

        discounted_capital_cost = self.calculate_discounted_lifetime_capital_cost(
            discount_rate=discount_rate, discount_base_year=discount_base_year
        )
        discounted_maintenance_cost = self.calculate_discounted_lifetime_maintenance_cost(
            discount_rate=discount_rate, discount_base_year=discount_base_year
        )

        #  unit cost portion only of discounted running cost at the trajectory's existing shape
        discounted_price_only_running_cost = self.calculate_discounted_lifetime_running_cost(
            heat_demand=heat_demand,
            energy_price_trajectory=energy_price_trajectory,
            standing_charge=0.0,
            discount_rate=discount_rate,
            discount_base_year=discount_base_year,
        )

        # standing charge component
        annual_standing_charge_in_pounds = standing_charge / 100 * 365
        discounted_standing_charge_cost = sum(
            annual_standing_charge_in_pounds
            * self._discount_factor(year=year, discount_base_year=discount_base_year, discount_rate=discount_rate)
            for year in self.operating_years
        )

        annuity_factor = self._annuity_factor(discount_rate=discount_rate, n=self.lifespan)

        eac_fixed_components = annuity_factor * (
            discounted_capital_cost + discounted_maintenance_cost + discounted_standing_charge_cost
        )

        eac_running_cost_at_original_prices = annuity_factor * discounted_price_only_running_cost

        # target_eac = eac_fixed_components + k * eac_running_cost_at_original_prices
        # solve for scale factor k
        required_scale_factor = (target_eac - eac_fixed_components) / eac_running_cost_at_original_prices

        return {
            year: energy_price_trajectory.get_price(year=year) * required_scale_factor for year in self.operating_years
        }
