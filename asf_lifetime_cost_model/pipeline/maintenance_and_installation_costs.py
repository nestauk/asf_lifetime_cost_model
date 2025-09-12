"""Maintenance and installation cost calculation.

Functions to handle cost computations for the ASF lifetime cost model including:
- Total maintenance costs
- Upfront installation costs
"""

# package imports
import pandas as pd

# local imports
from asf_lifetime_cost_model import config


def create_cost_reduction_data(
    annual_cost_reduction: float,
    reference_year: int = config.get("cost_data_reference_year"),
    max_year: int = config.get("installation_year_max"),
) -> dict:
    """Creates cost reduction data for a heating system over the years by applying an annual cost reduction rate.

    These values can be used to adjust the installation costs of a heating system based on the cost of
    installation is a specific reference year.

    Args:
        annual_cost_reduction (float): The annual cost reduction rate. Should be a value between 0 and 1.
        reference_year (int, optional): The year from which the reduction starts.
            Defaults to config.get("cost_data_reference_year").
        max_year (int, optional): The maximum year for which the reduction is calculated.
            Defaults to config.get("installation_year_max").

    Returns:
        dict: A dictionary with years as keys and the reduction factor as values.
    """
    reduction_per_year = {reference_year: 1}  # no reduction in the reference year

    for year in range(reference_year + 1, max_year + 1):
        reduction_per_year[year] = (1 - annual_cost_reduction) * reduction_per_year[year - 1]

    return reduction_per_year


def get_ashp_subsidy_value(subsidy_data: pd.DataFrame, subsidy_model: str, purchase_year: int) -> float:
    """Gets the subsidy value for a specific subsidy model.

    Args:
        subsidy_data (pd.DataFrame): DataFrame containing subsidy values for different models and years.
        subsidy_model (str): The model of the subsidy.
            Models include: "flat", "slow stepdown", "fast stepdown", "high", "zero from 2028",
            "smallest", "no subsidy".
        purchase_year (int): The year in which the heating system is purchased and installed.

    Raises:
        ValueError: If the subsidy model is not supported.

    Returns:
        float: The subsidy value for the specified model.
    """
    supported_models = config.get("ashp_subsidy_options")

    if subsidy_model not in supported_models:
        raise ValueError(f"Unsupported subsidy model: {subsidy_model}. Supported models are: {supported_models}")

    subsidy_value = subsidy_data[subsidy_data["model"] == subsidy_model][str(purchase_year)].iloc[0]

    return subsidy_value


def compute_cost_with_loan(upfront_cost: float, life_span: int, loan_interest_rate: float) -> float:
    """Computes the total cost of a heating system when purchased with a loan.

    Args:
        upfront_cost (float): The upfront cost of the heating system.
        life_span (int): Number of years the heating system is assumed to be operational.
        loan_interest_rate (float): Loan interest rate, as a decimal (e.g. 5% interest rate should be inputted
            as 0.05).

    Returns:
        float: The total cost of the heating system when purchased with a loan.
    """
    loan_amount = upfront_cost
    loan_term = life_span  # loan repayment period is assumed to be over lifetime
    annual_loan_payment = (loan_amount * loan_interest_rate) / (1 - ((1 + loan_interest_rate) ** -loan_term))
    return annual_loan_payment * loan_term
