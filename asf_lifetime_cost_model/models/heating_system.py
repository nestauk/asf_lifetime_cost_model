"""Model of a heating system installed in a household: costs, financing, and lifetime economics.

Represents an air-to-water heat pump or gas boiler, deriving fuel from
system_type and looking up installation cost and subsidy from trajectory
objects for the chosen installation_year. Provides running, maintenance,
lifetime, and annualised cost calculations, with optional loan financing.
"""

from typing import Optional

from asf_lifetime_cost_model import config
from asf_lifetime_cost_model.models.energy_price_trajectory import EnergyPriceTrajectory
from asf_lifetime_cost_model.models.installation_cost_trajectory import InstallationCostTrajectory
from asf_lifetime_cost_model.models.subsidy_trajectory import SubsidyTrajectory

FUEL_BY_SYSTEM_TYPE = config["fuel_by_system_type"]


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
        maintenance_cost_per_visit: float,  # £
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

        self.system_type = system_type
        self.fuel = FUEL_BY_SYSTEM_TYPE[system_type]
        self.installation_year = installation_year
        self.lifespan = lifespan
        self.efficiency = efficiency

        self.installation_cost = installation_cost_trajectory.get_cost(installation_year)
        self.subsidy = subsidy_trajectory.get_subsidy(installation_year)
        self.upfront_cost = self.installation_cost - self.subsidy

        self.maintenance_cost_per_visit = maintenance_cost_per_visit
        self.maintenance_annual_frequency = maintenance_annual_frequency

        self.interest_rate = interest_rate
        self.loan_term = loan_term
        self.is_financed = interest_rate is not None

    def _validate_fuel_match(self, energy_price_trajectory: EnergyPriceTrajectory) -> None:
        """Ensure energy_price_trajectory's fuel matches this system's fuel before using it in a calculation."""
        if energy_price_trajectory.fuel != self.fuel:
            raise ValueError(
                f"energy_price_trajectory fuel ({energy_price_trajectory.fuel!r}) "
                f"does not match HeatingSystem fuel ({self.fuel!r})"
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
        """Running cost for a single year = energy demand x fuel price that year. Heat demand in kWh/year."""
        self._validate_fuel_match(energy_price_trajectory)
        energy_demand = self.calculate_energy_demand(heat_demand)
        return energy_demand * energy_price_trajectory.get_price(year)

    def calculate_lifetime_running_cost(
        self, heat_demand: float, energy_price_trajectory: EnergyPriceTrajectory
    ) -> float:
        """Total running cost (fuel only) summed across every year of operation. Heat demand in kWh/year."""
        operating_years = self._get_operating_years(energy_price_trajectory)
        return sum(self.calculate_running_cost(year, heat_demand, energy_price_trajectory) for year in operating_years)

    def calculate_maintenance_cost(self) -> float:
        """Expected annual maintenance cost (e.g. cost_per_visit=100, frequency=0.5 -> £50/year average)."""
        return self.maintenance_cost_per_visit * self.maintenance_annual_frequency

    def calculate_annual_loan_repayment(self) -> float:
        """Aannual repayment for financing upfront_cost via a loan.

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

    def calculate_lifetime_cost(self, heat_demand: float, energy_price_trajectory: EnergyPriceTrajectory) -> float:
        """Total cost over the system's lifespan.

        Includes running cost and maintenance cost summed across every year of operation,
        plus either the upfront cost paid once (unfinanced) or annual loan repayments summed
        over the loan term (financed).

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
        """Annualised total cost over the system's lifespan.

        Equals the lifetime cost (upfront/financing + running + maintenance) spread evenly across
        every year of operation.

        Heat demand must be provided in kWh/year.
        """
        operating_years = self._get_operating_years(energy_price_trajectory)
        total_lifetime_cost = self.calculate_lifetime_cost(heat_demand, energy_price_trajectory)

        return total_lifetime_cost / len(operating_years)

    def __repr__(self) -> str:
        """Return a string representation showing the system's key attributes and costs."""
        return (
            f"HeatingSystem(type={self.system_type!r}, fuel={self.fuel!r}, "
            f"installation_year={self.installation_year}, lifespan={self.lifespan}, "
            f"efficiency={self.efficiency}, upfront_cost={self.upfront_cost}, "
            f"maintenance_cost_per_visit={self.maintenance_cost_per_visit}, "
            f"maintenance_annual_frequency={self.maintenance_annual_frequency}, "
            f"is_financed={self.is_financed})"
        )
