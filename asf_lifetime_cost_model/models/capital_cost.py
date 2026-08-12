"""Capital (upfront/loan) cost calculations for a HeatingSystem.

Split out of heating_system.py to keep HeatingSystem's core construction and
discounting logic readable. CapitalCostMixin is mixed into HeatingSystem, so
these remain instance methods (self is a HeatingSystem) with access to its
attributes (capital_cost, interest_rate, loan_term, is_financed, ...) and
_discount_factor/_annuity_factor/_resolve_discount_base_year/_annualise
helpers.
"""

from typing import TYPE_CHECKING, Optional

from asf_lifetime_cost_model import config

if TYPE_CHECKING:
    from asf_lifetime_cost_model.models.heating_system import HeatingSystem

DEFAULT_DISCOUNT_RATE = config["default_discount_rate"]


class CapitalCostMixin:
    """Adds capital (upfront/loan) cost calculations to HeatingSystem."""

    def calculate_annual_loan_repayment(self: "HeatingSystem") -> float:
        """Annual repayment for financing capital_cost via a loan.

        Uses annuity formula over loan_term years at interest_rate.
        Raises if this system isn't financed.
        """
        if not self.is_financed:
            raise ValueError("This HeatingSystem was not financed via a loan (interest_rate/loan_term were None)")

        if self.interest_rate == 0:
            return self.capital_cost / self.loan_term

        r = self.interest_rate
        n = self.loan_term
        return self.capital_cost * r / (1 - (1 + r) ** -n)

    def calculate_discounted_loan_repayment(
        self: "HeatingSystem",
        year: int,
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        discount_base_year: Optional[int] = None,
    ) -> float:
        """Loan repayment for a single year, discounted back to discount_base_year.

        Repayments run from installation_year + 1 through installation_year +
        loan_term (i.e. the first repayment falls one year after installation.
        Interest accrues from day one, but nothing is due until one full
        period has elapsed.

        Raises if this system isn't financed, or if year falls outside the
        loan's actual repayment period.
        """
        if not self.is_financed:
            raise ValueError("This HeatingSystem was not financed via a loan (interest_rate/loan_term were None)")

        repayment_years = range(self.installation_year + 1, self.installation_year + self.loan_term + 1)
        if year not in repayment_years:
            raise ValueError(
                f"year {year} is outside this loan's repayment period "
                f"({repayment_years[0]}-{repayment_years[-1]}, loan_term={self.loan_term})"
            )

        discount_base_year = self._resolve_discount_base_year(discount_base_year)
        annual_repayment = self.calculate_annual_loan_repayment()
        return annual_repayment * self._discount_factor(
            year=year, discount_base_year=discount_base_year, discount_rate=discount_rate
        )

    def calculate_lifetime_loan_interest(self: "HeatingSystem") -> float:
        """Total interest paid over the life of the loan (total repayments minus principal borrowed).

        Raises if this system isn't financed.
        """
        if not self.is_financed:
            raise ValueError("This HeatingSystem was not financed via a loan (interest_rate/loan_term were None)")

        total_repayments = self.calculate_annual_loan_repayment() * self.loan_term
        return total_repayments - self.capital_cost

    def calculate_discounted_lifetime_loan_interest(
        self: "HeatingSystem",
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        discount_base_year: Optional[int] = None,
    ) -> float:
        """Total interest cost of the loan, in present-value terms, discounted back to discount_base_year.

        Equals calculate_discounted_lifetime_capital_cost minus the capital_cost
        (principal) discounted for the installation_year alone — i.e. the extra
        present-value cost of financing versus paying capital_cost in cash.

        Raises if this system isn't financed.
        """
        if not self.is_financed:
            raise ValueError("This HeatingSystem was not financed via a loan (interest_rate/loan_term were None)")

        discount_base_year = self._resolve_discount_base_year(discount_base_year)

        discounted_capital_cost = self.calculate_discounted_lifetime_capital_cost(
            discount_rate=discount_rate, discount_base_year=discount_base_year
        )
        discounted_principal = self.capital_cost * self._discount_factor(
            year=self.installation_year, discount_base_year=discount_base_year, discount_rate=discount_rate
        )
        return discounted_capital_cost - discounted_principal

    def calculate_lifetime_capital_cost(self: "HeatingSystem") -> float:
        """Total (undiscounted) capital cost over the system's lifespan.

        Equals capital_cost if unfinanced, or total loan repayments
        (principal + interest) if financed.
        """
        if self.is_financed:
            return self.calculate_annual_loan_repayment() * self.loan_term
        return self.capital_cost

    def calculate_discounted_lifetime_capital_cost(
        self: "HeatingSystem",
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        discount_base_year: Optional[int] = None,
    ) -> float:
        """Capital cost over the system's lifespan, discounted back to discount_base_year.

        If unfinanced: the single capital_cost lump sum, discounted for the
        installation_year alone. If financed: the sum of annual loan
        repayments (via calculate_discounted_loan_repayment), each
        discounted individually for the year it's paid.
        """
        discount_base_year = self._resolve_discount_base_year(discount_base_year)

        if self.is_financed:
            repayment_years = range(self.installation_year + 1, self.installation_year + self.loan_term + 1)
            return sum(
                self.calculate_discounted_loan_repayment(
                    year=year, discount_rate=discount_rate, discount_base_year=discount_base_year
                )
                for year in repayment_years
            )
        return self.capital_cost * self._discount_factor(
            year=self.installation_year, discount_base_year=discount_base_year, discount_rate=discount_rate
        )

    def calculate_annualised_discounted_lifetime_capital_cost(
        self: "HeatingSystem",
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        discount_base_year: Optional[int] = None,
    ) -> float:
        """Equivalent Annual Cost of just the capital cost component (principal + interest if financed)."""
        npv = self.calculate_discounted_lifetime_capital_cost(
            discount_rate=discount_rate, discount_base_year=discount_base_year
        )
        return self._annualise(npv, discount_rate=discount_rate)

    def calculate_annualised_discounted_lifetime_loan_interest(
        self: "HeatingSystem",
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        discount_base_year: Optional[int] = None,
    ) -> float:
        """Equivalent Annual Cost of just the loan interest component. Raises if unfinanced."""
        npv = self.calculate_discounted_lifetime_loan_interest(
            discount_rate=discount_rate, discount_base_year=discount_base_year
        )
        return self._annualise(npv, discount_rate=discount_rate)
