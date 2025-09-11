"""Cost computations.

Functions to handle cost computations for the ASF lifetime cost model including:
- Total maintenance costs
- Upfront installation costs
- Running costs
- Total lifetime costs computation
as a total and as a breakdown per year in the lifetime of the heating system.
"""

# package imports
from typing import Union

# local imports
from asf_lifetime_cost_model import config
from asf_lifetime_cost_model.getters import data_getters


def compute_total_maintenance_cost(
    maintenance_cost: float, maintenance_frequency_per_year: float, life_span: int
) -> float:
    """Computes the total maintenance cost for technology.

    This is done given the cost of each maintenance session, number of times the heating system
    is serviced each year and the expected lifetime.

    Args:
        maintenance_cost (float): The cost of one maintenance servicing session for heating system.
        maintenance_frequency_per_year (float): Average number of times the heating system is serviced each year.
        life_span (int): Number of years the heating system is assumed to be operational.

    Returns:
        float: The total maintenance costs over the specified number of years.
    """
    return maintenance_cost * maintenance_frequency_per_year * life_span


def create_cost_reduction_data(
    annual_cost_reduction: float,
    reference_year: int = config.get("cost_data_reference_year"),
    max_year: int = config.get("cost_year_max"),
) -> dict:
    """Creates cost reduction data for a heating system over the years by applying an annual cost reduction rate.

    These values can be used to adjust the installation costs of a heating system based on the cost of
    installation is a specific reference year.

    Args:
        annual_cost_reduction (float): The annual cost reduction rate. Should be a value between 0 and 1.
        reference_year (int, optional): The year from which the reduction starts.
            Defaults to config.get("cost_data_reference_year").
        max_year (int, optional): The maximum year for which the reduction is calculated.
            Defaults to config.get("cost_year_max").

    Returns:
        dict: A dictionary with years as keys and the reduction factor as values.
    """
    reduction_per_year = {reference_year: 1}  # no reduction in the reference year

    for year in range(reference_year + 1, max_year + 1):
        reduction_per_year[year] = (1 - annual_cost_reduction) * reduction_per_year[year - 1]

    return reduction_per_year


def get_installation_cost(heating_system: str, archetype: str, decile: int = None) -> float:
    """Gets the cost of a heating system for a specific archetype (and decile where applicable).

    Args:
        heating_system (str): heating system.
            Takes "ashp" (for air source heat pump) or "boiler" (for gas boiler).
        archetype (str): Propery archetype
        decile (int, optional): cost decile, only used for air source heat pumps.
            Takes multiples of 10 between 10 and 90, inclusive.

    Raises:
        ValueError: If the heating system inputed is not supported
                    or the decile is not a multiple of 10 between 10 and 90.

    Returns:
        float: The cost of the heating system for the specified archetype (and decile where applicable).
    """
    if decile is not None and (decile < 10 or decile > 90 or decile % 10 != 0):
        raise ValueError("Decile must be a multiple of 10 between 10 and 90, inclusive.")

    if heating_system == "ashp":
        costs_data = data_getters.get_ashp_installation_costs()
        cost_value = costs_data[costs_data["archetype_label"] == archetype][f"cost_percentile_{decile}"].iloc[0]
    elif heating_system == "boiler":
        costs_data = data_getters.get_gas_boiler_installation_costs()
        cost_value = costs_data[(costs_data["archetype_label"] == archetype)]["cost"].iloc[0]
    else:
        raise ValueError(
            f"Unsupported heating system: {heating_system}. Supported heating systems are `ashp` and `boiler`."
        )

    return cost_value


def get_ashp_subsidy_value(subsidy_model: str, purchase_year: int) -> float:
    """Gets the subsidy value for a specific subsidy model.

    Args:
        subsidy_model (str): The model of the subsidy.
            Models include: "flat", "slow stepdown", "fast stepdown", "high", "zero from 2028",
            "smallest", "no subsidy".
        purchase_year (int): The year in which the heating system is installed.

    Raises:
        ValueError: If the subsidy model is not supported.

    Returns:
        float: The subsidy value for the specified model.
    """
    supported_models = config.get("ashp_subsidy_options")

    if subsidy_model not in supported_models:
        raise ValueError(f"Unsupported subsidy model: {subsidy_model}. Supported models are: {supported_models}")

    subsidy_data = data_getters.get_ashp_subsidy_options_data()
    subsidy_value = subsidy_data[subsidy_data["model"] == subsidy_model][str(purchase_year)].iloc[0]

    return subsidy_value


def compute_upfront_cost(
    heating_system: str,
    archetype: str,
    annual_cost_reduction: float,
    purchase_year: int,
    life_span: int = None,
    decile: int = None,
    subsidy_model_or_input_values: Union[str, dict] = "no subsidy",
    purchase_with_loan: bool = False,
    loan_interest_rate: float = 0.0,
) -> float:
    """Computes the upfront costs of installing a heating system.

    Args:
        heating_system (str): heating system.
            Takes "ashp" (for air source heat pump) or "boiler" (for gas boiler).
        archetype (str): Property archetype
            Takes: TODO: add final list of archetypes.
        life_span (int): Number of years the heating system is assumed to be operational.
            Defaults to None. Only required when purchase_with_loan is True.
        decile (int, optional): cost decile, only used for air source heat pumps.
        annual_cost_reduction (float): how much the cost of installing the heating system reduces each year
            in comparison to the previous year.
        purchase_year (int): the year in which the heating system is installed.
        subsidy_model_or_input_values (Union[str, dict], optional): The ASHP subsidy model to get the subsidy
            to be subtracted OR a dictionary of subsidy values for each year.
            Models include: "flat", "slow stepdown", "fast stepdown", "high", "zero from 2028",
            "smallest", "no subsidy".
        purchase_with_loan (bool): Whether heating system is purchased with a loan. Defaults to False.
            Loan repayment period is set equal to provided life span of heating system.
        loan_interest_rate (float): Loan interest rate, as a decimal (e.g. 5% interest rate should be inputted
            as 0.05). Defaults to 0.0.

    Raises:
        ValueError: If the heating system inputed is not supported or the year is above or equal to 2035.

    Returns:
        float: Upfront cost of installing a heating system.
    """
    if purchase_year >= config.get("cost_year_max"):
        raise ValueError(f"Purchase year must be before {config.get('cost_year_max')}.")

    if heating_system not in ["ashp", "boiler"]:
        raise ValueError(
            f"Unsupported heating system: {heating_system}. Supported heating systems are `ashp` and `boiler`."
        )

    # Get installation cost for a specific heating system, archetype, and decile (where applicable)
    installation_cost = get_installation_cost(heating_system=heating_system, archetype=archetype, decile=decile)

    # Apply installation cost reduction assumption
    cost_reduction_data = create_cost_reduction_data(annual_cost_reduction=annual_cost_reduction)
    cost_reduction_value = cost_reduction_data[purchase_year]
    installation_cost = installation_cost * cost_reduction_value

    # ASHP with preset subsidy model
    if (type(subsidy_model_or_input_values) is str) and (heating_system == "ashp"):
        subsidy_value = get_ashp_subsidy_value(subsidy_model=subsidy_model_or_input_values, purchase_year=purchase_year)
        upfront_cost = installation_cost - subsidy_value
    # ASHP with custom subsidy model
    elif heating_system == "ashp":  # dictionary provided
        if purchase_year not in subsidy_model_or_input_values.keys():
            raise ValueError(f"Please provide subsidy value for purchase year: {purchase_year}")
        return installation_cost - subsidy_model_or_input_values[purchase_year]
    # Boilers
    else:  # boilers
        upfront_cost = installation_cost

    if purchase_with_loan:
        if life_span is None:
            raise ValueError("Please provide `life_span` in years when purchasing with loans.")
        if loan_interest_rate != 0.0:
            loan_amount = upfront_cost
            loan_term = life_span  # loan repayment period is assumed to be over lifetime
            annual_loan_payment = (loan_amount * loan_interest_rate) / (1 - ((1 + loan_interest_rate) ** -loan_term))
            return annual_loan_payment * loan_term
        else:  # 0% interest
            return upfront_cost
    else:  # not purchasing with loan
        return upfront_cost


def compute_total_lifetime_costs(
    heating_system: str,
    archetype: str,
    annual_cost_reduction: float,
    purchase_year: int,
    maintenance_cost: float,
    maintenance_frequency_per_year: float,
    life_span: int,
    subsidy_model_or_input_values: Union[str, dict] = "no subsidy",
    decile: int = None,
    purchase_with_loan: bool = False,
    loan_interest_rate: float = 0.0,
) -> float:
    """Computes the lifetime cost of a heating system over its lifetime.

    Args:
        heating_system (str): heating system.
            Takes "ashp" (for air source heat pump) or "boiler" (for gas boiler).
        archetype (str): Property archetype
            Takes: TODO: add final list of archetypes.
        annual_cost_reduction (float): how much the cost of installing the heating system reduces each year
            in comparison to the previous year.
        purchase_year (int): the year in which the heating system is installed.
        maintenance_cost (float): The cost of one maintenance servicing session for heating system.
        maintenance_frequency_per_year (float): Average number of times the heating system is serviced each year.
        life_span (int): Number of years the heating system is assumed to be operational.
        subsidy_model_or_input_values (Union[str, dict], optional): The ASHP subsidy model to get the subsidy
            to be subtracted OR a dictionary of subsidy values for each year.
            Models include: "flat", "slow stepdown", "fast stepdown", "high", "zero from 2028",
            "smallest", "no subsidy".
        decile (int, optional): cost decile, only used for air source heat pumps.
        purchase_with_loan (bool): Whether heating system is purchased with a loan. Defaults to False.
            Loan repayment period is set equal to provided life span of heating system.
        loan_interest_rate (float): Loan interest rate, as a decimal (e.g. 5% interest rate should be inputted
            as 0.05). Defaults to 0.0.

    Raises:
        ValueError: If the subsidy model is not applicable for the heating system.

    Returns:
        float: The total costs over the specified number of years.
    """
    if (heating_system == "boiler") and (subsidy_model_or_input_values != "no subsidy"):
        raise ValueError("Subsidy model is only applicable for air source heat pumps. Choose 'no subsidy'.")

    if (
        (heating_system == "ashp")
        and type(subsidy_model_or_input_values) is str
        and subsidy_model_or_input_values not in config.get("ashp_subsidy_options")
    ):
        supported_models = config.get("ashp_subsidy_options")
        raise ValueError(
            f"Unsupported subsidy model: {subsidy_model_or_input_values}. Supported models are: {supported_models}."
        )

    upfront_cost = compute_upfront_cost(
        heating_system=heating_system,
        life_span=life_span,
        archetype=archetype,
        decile=decile,
        annual_cost_reduction=annual_cost_reduction,
        purchase_year=purchase_year,
        subsidy_model_or_input_values=subsidy_model_or_input_values,
        purchase_with_loan=purchase_with_loan,
        loan_interest_rate=loan_interest_rate,
    )
    maintenance_cost = compute_total_maintenance_cost(
        maintenance_cost=maintenance_cost,
        maintenance_frequency_per_year=maintenance_frequency_per_year,
        life_span=life_span,
    )

    # running_costs = compute_running_costs()

    return upfront_cost + maintenance_cost


def create_annualised_cost_time_series(cost_value: float, life_span: int, purchase_year: int) -> dict:
    """Creates a time series of annualised cost per year in the lifetime of the heating system.

    Args:
        cost_value (float): The total cost value to be annualised.
        life_span (int): Number of years the heating system is assumed to be operational.
        purchase_year (int): The year in which the heating system is installed.

    Returns:
        dict: A dictionary with years as keys and cost values as values.
    """
    cost_per_year = cost_value / life_span
    annualised_cost_time_series = dict.fromkeys(
        range(purchase_year, purchase_year + life_span),
        cost_per_year,
    )

    return annualised_cost_time_series
