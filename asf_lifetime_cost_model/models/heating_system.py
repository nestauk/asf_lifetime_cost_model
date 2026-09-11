"""Model of a heating system installed in a household: costs, financing, and lifetime economics.

Represents a heating system (current supported types are air-to-water heat pump or gas boiler)
deriving fuel from system_type and looking up installation cost and subsidy from trajectory
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
from asf_lifetime_cost_model.models.capital_cost import CapitalCostMixin
from asf_lifetime_cost_model.models.lifetime_cost import LifetimeCostMixin
from asf_lifetime_cost_model.models.maintenance_cost import MaintenanceCostMixin
from asf_lifetime_cost_model.models.parity_solvers import ParitySolverMixin
from asf_lifetime_cost_model.models.running_cost import RunningCostMixin
from asf_lifetime_cost_model.models.trajectory import (
    EnergyPriceTrajectory,
    InstallationCostTrajectory,
    SubsidyTrajectory,
)

FUEL_BY_SYSTEM_TYPE = config["fuel_by_system_type"]
DEFAULT_DISCOUNT_RATE = config["default_discount_rate"]


class HeatingSystem(RunningCostMixin, CapitalCostMixin, MaintenanceCostMixin, LifetimeCostMixin, ParitySolverMixin):
    """Represents a heating system installed in a household.

    Currently supported system types are air-to-water heat pump or gas boiler.

    Heating systems are characterised by technology type, fuel, efficiency,
    capital cost, maintenance cost, and lifespan.

    Fuel is derived automatically from system_type (heat pumps run on
    electricity, boilers run on gas - defined in config["fuel_by_system_type"]).

    Installation cost and subsidy are looked up from InstallationCostTrajectory
    and SubsidyTrajectory objects for this system's installation_year. Efficiency and
    maintenance cost/frequency are fixed at the point of installation. Only
    energy prices vary year-to-year.

    Years of its lifetime is constructed based on its installation year and lifespan.

    All three trajectory objects passed in must already be in real terms
    (price_basis="real") and share the same base_year, since costs from
    different years are summed together and discounted using a single real
    discount rate — mixing nominal and real cashflows, or trajectories with
    different base years, would silently give a wrong answer.

    Optionally financed via a loan (interest_rate + loan_term): if provided,
    the loan is assumed to cover 100% of capital_cost as no deposit is
    modeled. Repayments begin one year after installation (interest accrues
    from day one, but nothing is due until one full period has elapsed),
    spread evenly over loan_term years using the standard annuity formula.

    Cost calculations are split across sibling mixins, each in its own module, and
    combined here via multiple inheritance so they remain plain instance methods:
    - RunningCostMixin (running_cost.py): fuel/energy running costs.
    - CapitalCostMixin (capital_cost.py): capital cost and loan repayments.
    - MaintenanceCostMixin (maintenance_cost.py): maintenance costs.
    - LifetimeCostMixin (lifetime_cost.py): totals combining the three mixins above.
    - ParitySolverMixin (parity_solvers.py): solves for the subsidy or electricity
      price needed to reach a target Equivalent Annual Cost.
    This class itself owns construction, validation, and the shared discounting
    functions (_discount_factor, _annuity_factor, ...) that every mixin relies on.
    """

    # --- Construction & validation ---

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
        loan_term: Optional[int] = None,  # years to repay over, starting 1 year after installation. None = no loan
        # NOTE: if financed, the loan is assumed to cover 100% of capital_cost and no deposit is modeled.
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

        self._validate_real_basis(trajectory=installation_cost_trajectory, name="installation_cost_trajectory")
        self._validate_real_basis(trajectory=subsidy_trajectory, name="subsidy_trajectory")

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
        self.operating_years = range(self.installation_year, self.installation_year + self.lifespan)

        self.installation_cost = installation_cost_trajectory.get_cost(year=installation_year)
        self.subsidy = subsidy_trajectory.get_subsidy(year=installation_year)
        self.capital_cost = self.installation_cost - self.subsidy
        # Capital cost has a floor of £0, a subsidy larger than installation_cost is
        # treated as fully covering the cost (household pays nothing), not as a
        # negative cost / net payment to the household
        self.capital_cost = max(0.0, self.installation_cost - self.subsidy)

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

    def _validate_energy_price_trajectory(self, energy_price_trajectory: EnergyPriceTrajectory) -> None:
        """Ensure energy_price_trajectory's attributes matches that of the heating system.

        Ensures correctly matched fuel, is in real terms, shares base_year, and covers this system's
        full operating_years range.
        """
        if energy_price_trajectory.fuel != self.fuel:
            raise ValueError(
                f"energy_price_trajectory fuel ({energy_price_trajectory.fuel!r}) "
                f"does not match HeatingSystem fuel ({self.fuel!r})"
            )
        self._validate_real_basis(trajectory=energy_price_trajectory, name="energy_price_trajectory")
        if energy_price_trajectory.base_year != self.base_year:
            raise ValueError(
                f"energy_price_trajectory base_year ({energy_price_trajectory.base_year}) "
                f"does not match HeatingSystem base_year ({self.base_year})"
            )

        last_operating_year = self.operating_years[-1]
        last_covered_year = energy_price_trajectory.prices.index.max()
        if last_operating_year > last_covered_year:
            raise ValueError(
                f"HeatingSystem's operating_years run through {last_operating_year} "
                f"(installation_year={self.installation_year} + lifespan={self.lifespan}), "
                f"but energy_price_trajectory only covers up to {last_covered_year}. "
                "Extend energy_price_trajectory's coverage or reduce lifespan."
            )

    def _validate_year_in_operating_years(self, year: int) -> None:
        """Ensure a given year falls within this system's operating_years range."""
        if year not in self.operating_years:
            raise ValueError(
                f"year {year} is outside this HeatingSystem's operating_years "
                f"({self.operating_years[0]}-{self.operating_years[-1]}, "
                f"installation_year={self.installation_year}, lifespan={self.lifespan})"
            )

    # --- Discounting helpers ---

    @staticmethod
    def _discount_factor(year: int, discount_base_year: int, discount_rate: float) -> float:
        """Real discount factor: 1 / (1 + discount_rate) ** (year - discount_base_year)."""
        return 1 / (1 + discount_rate) ** (year - discount_base_year)

    @staticmethod
    def _annuity_factor(discount_rate: float, n: int) -> float:
        """Factor that converts a lump-sum present value into a level annual payment.

        Uses the annuity-due convention (payment at the start of each period,
        t=0 through n-1), where the first year (t=0, the installation year) is always
        undiscounted. This differs from the standard "ordinary annuity"
        formula (payment at the end of each period, t=1 through n, used e.g.
        for constant mortgage repayments) by a factor of (1 + discount_rate).
        """
        if discount_rate == 0:
            return 1 / n
        return discount_rate / ((1 + discount_rate) * (1 - (1 + discount_rate) ** -n))

    def _resolve_discount_base_year(self, discount_base_year: Optional[int]) -> int:
        """Default discount_base_year to this system's installation_year when not given."""
        return discount_base_year if discount_base_year is not None else self.installation_year

    def _annualise(self, npv: float, discount_rate: float) -> float:
        """Convert a present value into a level Equivalent Annual Cost over this system's lifespan."""
        return npv * self._annuity_factor(discount_rate=discount_rate, n=self.lifespan)

    # --- Representation ---

    def __repr__(self) -> str:
        """Return a string representation showing the system's key attributes and costs."""
        return (
            f"HeatingSystem(type={self.system_type!r}, fuel={self.fuel!r}, "
            f"installation_year={self.installation_year}, lifespan={self.lifespan}, "
            f"efficiency={self.efficiency}, capital_cost={self.capital_cost}, "
            f"maintenance_cost_per_visit={self.maintenance_cost_per_visit}, "
            f"maintenance_annual_frequency={self.maintenance_annual_frequency}, "
            f"is_financed={self.is_financed}, base_year={self.base_year})"
        )
