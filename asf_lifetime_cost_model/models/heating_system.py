"""Model of a heating system installed in a household: costs, financing, and lifetime economics.

Represents an air-to-water heat pump or gas boiler, deriving fuel from
system_type and looking up installation cost and subsidy from trajectory
objects for the chosen installation_year. Provides running, maintenance,
lifetime, and annualised cost calculations, with optional loan financing
and present-value discounting.

All calculations assume every trajectory passed in (installation_cost_trajectory,
subsidy_trajectory, energy_price_trajectory) is already in real terms
(price_basis="real"), sharing the same base_year, so costs from different
years can be safely summed and discounted using a single real discount rate.
"""

from typing import Optional, Union

from asf_lifetime_cost_model import config
from asf_lifetime_cost_model.models.energy_price_trajectory import EnergyPriceTrajectory
from asf_lifetime_cost_model.models.installation_cost_trajectory import InstallationCostTrajectory
from asf_lifetime_cost_model.models.subsidy_trajectory import SubsidyTrajectory

FUEL_BY_SYSTEM_TYPE = config["fuel_by_system_type"]
DEFAULT_DISCOUNT_RATE = config["default_discount_rate"]


class HeatingSystem:
    """Represents a heating system installed in a household.

    For example, an air-to-water heat pump or gas boiler, its type, fuel, efficiency,
    upfront cost, maintenance cost, and lifespan.

    Fuel is derived automatically from system_type (heat pumps run on
    electricity, boilers run on gas).

    Installation cost and subsidy are looked up from InstallationCostTrajectory
    and SubsidyTrajectory objects for this system's installation_year. Efficiency and
    maintenance cost/frequency are fixed at the point of installation. Only
    energy prices vary year-to-year.

    All three trajectory objects passed in must already be in real terms
    (price_basis="real") and share the same base_year, since costs from
    different years are summed together and discounted using a single real
    discount rate — mixing nominal and real cashflows, or trajectories with
    different base years, would silently give a wrong answer.

    Optionally financed via a loan (interest_rate + loan_term): if provided,
    upfront_cost is spread into equal annual repayments over the loan term
    instead of being paid as a lump sum in the installation year.
    """

    def __init__(
        self,
        system_type: str,  # e.g. "air_to_water_heat_pump", "gas_boiler"
        installation_year: int,  # 2026-2035
        lifespan: int,  # years
        efficiency: float,  # fixed at point of installation
        installation_cost_trajectory: InstallationCostTrajectory,
        subsidy_trajectory: SubsidyTrajectory,
        maintenance_cost_per_visit: float,  # £, real terms
        maintenance_annual_frequency: float,  # visits per year, e.g. 1.0 = annual, 0.5 = every 2 years
        interest_rate: Optional[float] = None,  # annual rate, e.g. 0.05 for 5%. None = no loan (pay upfront)
        loan_term: Optional[int] = None,  # years to repay over. None = no loan (pay upfront)
    ) -> None:
        """Instantiate heating system, looking up installation cost and subsidy for installation_year."""
        if system_type not in FUEL_BY_SYSTEM_TYPE:
            raise ValueError(f"Unknown system_type {system_type!r}; expected one of {list(FUEL_BY_SYSTEM_TYPE)}")
        if installation_cost_trajectory.system_type != system_type:
            raise ValueError(
                f"installation_cost_trajectory system_type ({installation_cost_trajectory.system_type!r}) "
                f"does not match HeatingSystem system_type ({system_type!r})"
            )
        if subsidy_trajectory.system_type != system_type:
            raise ValueError(
                f"subsidy_trajectory system_type ({subsidy_trajectory.system_type!r}) "
                f"does not match HeatingSystem system_type ({system_type!r})"
            )
        if (interest_rate is None) != (loan_term is None):
            raise ValueError("interest_rate and loan_term must both be provided, or both left as None")
        if loan_term is not None and loan_term <= 0:
            raise ValueError(f"loan_term must be a positive number of years, got {loan_term}")

        self._validate_real_basis(installation_cost_trajectory, "installation_cost_trajectory")
        self._validate_real_basis(subsidy_trajectory, "subsidy_trajectory")

        if installation_cost_trajectory.base_year != subsidy_trajectory.base_year:
            raise ValueError(
                f"installation_cost_trajectory base_year ({installation_cost_trajectory.base_year}) "
                f"does not match subsidy_trajectory base_year ({subsidy_trajectory.base_year})"
            )

        self.system_type = system_type
        self.fuel = FUEL_BY_SYSTEM_TYPE[system_type]
        self.installation_year = installation_year
        self.lifespan = lifespan
        self.efficiency = efficiency
        self.base_year = installation_cost_trajectory.base_year

        self.installation_cost = installation_cost_trajectory.get_cost(installation_year)
        self.subsidy = subsidy_trajectory.get_subsidy(installation_year)
        self.upfront_cost = self.installation_cost - self.subsidy

        self.maintenance_cost_per_visit = maintenance_cost_per_visit
        self.maintenance_annual_frequency = maintenance_annual_frequency

        self.interest_rate = interest_rate
        self.loan_term = loan_term
        self.is_financed = interest_rate is not None

    @staticmethod
    def _validate_real_basis(
        trajectory: Union[InstallationCostTrajectory, SubsidyTrajectory, EnergyPriceTrajectory], name: str
    ) -> None:
        """Ensure a trajectory object is in real terms before it's used in any cost calculation."""
        if trajectory.price_basis != "real":
            raise ValueError(
                f"{name} must be in real terms (price_basis='real') before use in HeatingSystem; "
                f"got price_basis={trajectory.price_basis!r}. Call .to_real(base_year, inflation_rate) first."
            )

    def _validate_fuel_match(self, energy_price_trajectory: EnergyPriceTrajectory) -> None:
        """Ensure energy_price_trajectory's fuel matches this system's fuel, is in real terms, and shares base_year."""
        if energy_price_trajectory.fuel != self.fuel:
            raise ValueError(
                f"energy_price_trajectory fuel ({energy_price_trajectory.fuel!r}) "
                f"does not match HeatingSystem fuel ({self.fuel!r})"
            )
        self._validate_real_basis(energy_price_trajectory, "energy_price_trajectory")
        if energy_price_trajectory.base_year != self.base_year:
            raise ValueError(
                f"energy_price_trajectory base_year ({energy_price_trajectory.base_year}) "
                f"does not match HeatingSystem base_year ({self.base_year})"
            )

    def _get_operating_years(self, energy_price_trajectory: EnergyPriceTrajectory) -> range:
        """Years this system is operating in, capped at the last year energy_price_trajectory covers."""
        self._validate_fuel_match(energy_price_trajectory)
        last_year = min(
            self.installation_year + self.lifespan - 1,
            energy_price_trajectory.prices.index.max(),
        )
        return range(self.installation_year, last_year + 1)

    def calculate_energy_demand(self, heat_demand: float) -> float:
        """Fuel input needed to meet a given heat demand, based on this system's fixed efficiency.

        Heat demand in kWh/year.
        """
        return heat_demand / self.efficiency

    def calculate_running_cost(
        self, year: int, heat_demand: float, energy_price_trajectory: EnergyPriceTrajectory
    ) -> float:
        """Running cost for a single year = energy demand x fuel price that year, converted to £.

        energy_price_trajectory prices are in p/kWh; this converts to £ so
        the result can be summed with installation_cost/subsidy/maintenance,
        which are all in £. Heat demand in kWh/year.
        """
        self._validate_fuel_match(energy_price_trajectory)
        energy_demand = self.calculate_energy_demand(heat_demand)
        price_in_pounds = energy_price_trajectory.get_price(year) / 100  # p/kWh -> £/kWh
        return energy_demand * price_in_pounds

    def calculate_lifetime_running_cost(
        self, heat_demand: float, energy_price_trajectory: EnergyPriceTrajectory
    ) -> float:
        """Total (undiscounted) running cost summed across every year of operation, in real terms.

        Heat demand in kWh/year.
        """
        operating_years = self._get_operating_years(energy_price_trajectory)
        return sum(self.calculate_running_cost(year, heat_demand, energy_price_trajectory) for year in operating_years)

    def calculate_annual_loan_repayment(self) -> float:
        """Annual repayment for financing upfront_cost via a loan.

        Uses annuity formula over loan_term years at interest_rate.
        Raises if this system isn't financed.
        """
        if not self.is_financed:
            raise ValueError("This HeatingSystem was not financed via a loan (interest_rate/loan_term were None)")

        if self.interest_rate == 0:
            return self.upfront_cost / self.loan_term

        r = self.interest_rate
        n = self.loan_term
        return self.upfront_cost * r / (1 - (1 + r) ** -n)

    def calculate_maintenance_cost(self) -> float:
        """Expected annual maintenance cost, real terms (e.g. cost_per_visit=100, frequency=0.5 -> £50/year average)."""
        return self.maintenance_cost_per_visit * self.maintenance_annual_frequency

    def calculate_lifetime_cost(self, heat_demand: float, energy_price_trajectory: EnergyPriceTrajectory) -> float:
        """Total (undiscounted, real-terms) cost over the system's lifespan.

        Includes running cost and maintenance cost summed across every year of operation,
        plus either the upfront cost paid once (unfinanced) or annual loan repayments summed
        over the loan term (financed). No time-value discounting applied — see
        calculate_discounted_lifetime_cost for present-value terms.

        Heat demand must be provided in kWh/year.
        """
        operating_years = self._get_operating_years(energy_price_trajectory)

        total_running_cost = self.calculate_lifetime_running_cost(heat_demand, energy_price_trajectory)
        total_maintenance_cost = self.calculate_maintenance_cost() * len(operating_years)

        if self.is_financed:
            total_financing_cost = self.calculate_annual_loan_repayment() * self.loan_term
        else:
            total_financing_cost = self.upfront_cost

        return total_financing_cost + total_running_cost + total_maintenance_cost

    def calculate_annualised_lifetime_cost(
        self, heat_demand: float, energy_price_trajectory: EnergyPriceTrajectory
    ) -> float:
        """Annualised (undiscounted, real-terms) total cost over the system's lifespan.

        Equals the lifetime cost (upfront/financing + running + maintenance) spread evenly across
        every year of operation.

        Heat demand must be provided in kWh/year.
        """
        operating_years = self._get_operating_years(energy_price_trajectory)
        total_lifetime_cost = self.calculate_lifetime_cost(heat_demand, energy_price_trajectory)

        return total_lifetime_cost / len(operating_years)

    def calculate_discounted_lifetime_cost(
        self,
        heat_demand: float,
        energy_price_trajectory: EnergyPriceTrajectory,
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        discount_base_year: Optional[int] = None,
    ) -> float:
        """Lifetime cost expressed in present-value terms.

        Every year's cost is discounted back to discount_base_year (defaults
        to this system's own installation_year) using the real discount
        factor 1 / (1 + discount_rate) ** (year - discount_base_year).

        Passing a single shared discount_base_year (e.g. 2026) lets you
        compare systems installed in different years on a like-for-like
        basis, since every cost — however far in the future it lands — gets
        expressed in the same year's present-value £. This is separate
        from each trajectory's own base_year (which strips out inflation);
        discount_base_year is the reference point for time-preference
        discounting only.

        - Upfront cost (unfinanced) is only discounted if discount_base_year
          is earlier than installation_year.
        - Loan repayments, running costs, and maintenance costs are each
          discounted individually per year, since they land in different
          future years.

        Heat demand in kWh/year.
        """
        discount_base_year = discount_base_year if discount_base_year is not None else self.installation_year
        operating_years = self._get_operating_years(energy_price_trajectory)

        def discount_factor(year: int) -> float:
            return 1 / (1 + discount_rate) ** (year - discount_base_year)

        if self.is_financed:
            annual_repayment = self.calculate_annual_loan_repayment()
            repayment_years = range(self.installation_year, self.installation_year + self.loan_term)
            discounted_financing_cost = sum(annual_repayment * discount_factor(year) for year in repayment_years)
        else:
            discounted_financing_cost = self.upfront_cost * discount_factor(self.installation_year)

        annual_maintenance_cost = self.calculate_maintenance_cost()
        discounted_running_and_maintenance = sum(
            (self.calculate_running_cost(year, heat_demand, energy_price_trajectory) + annual_maintenance_cost)
            * discount_factor(year)
            for year in operating_years
        )

        return discounted_financing_cost + discounted_running_and_maintenance

    def calculate_annualised_discounted_lifetime_cost(
        self,
        heat_demand: float,
        energy_price_trajectory: EnergyPriceTrajectory,
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        discount_base_year: Optional[int] = None,
    ) -> float:
        """Equivalent Annual Cost (EAC): a level annual amount, over the system's lifespan,
        whose present value equals calculate_discounted_lifetime_cost's result.

        Unlike calculate_annualised_lifetime_cost (which divides the
        undiscounted total by the number of years), this accounts
        for the fact that later years' costs are worth less today by using
        the standard annuity formula: EAC = NPV * r / (1 - (1 + r) ** -n).

        Heat demand in kWh/year.
        """
        npv = self.calculate_discounted_lifetime_cost(
            heat_demand, energy_price_trajectory, discount_rate, discount_base_year
        )
        n = self.lifespan

        if discount_rate == 0:
            return npv / n

        r = discount_rate
        return npv * r / (1 - (1 + r) ** -n)

    def __repr__(self) -> str:
        """Return a string representation showing the system's key attributes and costs."""
        return (
            f"HeatingSystem(type={self.system_type!r}, fuel={self.fuel!r}, "
            f"installation_year={self.installation_year}, lifespan={self.lifespan}, "
            f"efficiency={self.efficiency}, upfront_cost={self.upfront_cost}, "
            f"maintenance_cost_per_visit={self.maintenance_cost_per_visit}, "
            f"maintenance_annual_frequency={self.maintenance_annual_frequency}, "
            f"is_financed={self.is_financed}, base_year={self.base_year})"
        )
