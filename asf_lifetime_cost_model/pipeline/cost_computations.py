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


def compute_total_maintenance_cost(annual_maintenance_costs: float, life_span: int) -> float:
    """Computes the total maintenance cost for technology given the annual maintenance cost and the expected lifetime.

    Args:
        annual_maintenance_costs (float): The annual maintenance cost of the heating system.
        life_span (int): Number of years the heating system is assumed to be operational.

    Returns:
        float: The total maintenance costs over the specified number of years.
    """
    return annual_maintenance_costs * life_span


def creates_cost_reduction_data(
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
        raise ValueError(f"Unsupported heating system: {heating_system}")

    return cost_value


def get_ashp_subsidy_value(subsidy_model: str, installation_year: int) -> float:
    """Gets the subsidy value for a specific subsidy model.

    Args:
        subsidy_model (str): The model of the subsidy.
            Models include: "flat", "slow stepdown", "fast stepdown", "high", "zero from 2028",
            "smallest", "no subsidy".
        installation_year (int): The year in which the heating system is installed.

    Raises:
        ValueError: If the subsidy model is not supported.

    Returns:
        float: The subsidy value for the specified model.
    """
    supported_models = config.get("ashp_subsidy_options")

    if subsidy_model not in supported_models:
        raise ValueError(f"Unsupported subsidy model: {subsidy_model}. Supported models are: {supported_models}")

    subsidy_data = data_getters.get_ashp_subsidy_options_data()
    subsidy_value = subsidy_data[subsidy_data["model"] == subsidy_model][str(installation_year)].iloc[0]

    return subsidy_value


def compute_upfront_cost(
    heating_system: str,
    archetype: str,
    annual_cost_reduction: float,
    installation_year: int,
    decile: int = None,
    subsidy_model_or_value: Union[str, float] = 0,
) -> float:
    """Computes the upfront costs of installing a heating system.

    Args:
        heating_system (str): heating system.
            Takes "ashp" (for air source heat pump) or "boiler" (for gas boiler).
        archetype (str): Property archetype
            Takes: TODO: add final list of archetypes.
        decile (int, optional): cost decile, only used for air source heat pumps.
        annual_cost_reduction (float): how much the cost of installing the heating system reduces each year
            in comparison to the previous year.
        installation_year (int): the year in which the heating system is installed.
        subsidy_model_or_value (Union[str, float], optional): The subsidy model to get the subsidy to be subtracted
            OR a fixed subsidy value.
            Models include: "flat", "slow stepdown", "fast stepdown", "high", "zero from 2028",
            "smallest", "no subsidy".

    Raises:
        ValueError: If the heating system inputed is not supported or the year is above or equal to 2035.

    Returns:
        float: Upfront cost of installing a heating system.
    """
    # Get installation cost for a specific heating system, archetype, and decile (where applicable)
    installation_cost = get_installation_cost(heating_system=heating_system, archetype=archetype, decile=decile)

    cost_reduction_data = creates_cost_reduction_data(annual_cost_reduction=annual_cost_reduction)
    cost_reduction_value = cost_reduction_data[installation_year]

    installation_cost = installation_cost * cost_reduction_value

    if (type(subsidy_model_or_value) is str) and (heating_system == "ashp"):
        subsidy_value = get_ashp_subsidy_value(
            subsidy_model=subsidy_model_or_value, installation_year=installation_year
        )
        return installation_cost - subsidy_value
    else:  # float provided
        return installation_cost - subsidy_model_or_value


def compute_total_lifetime_costs(
    heating_system: str,
    archetype: str,
    annual_cost_reduction: float,
    installation_year: int,
    annual_maintenance_costs: float,
    life_span: int,
    subsidy_model_or_value: Union[str, float] = 0,
    decile: int = None,
) -> float:
    """Computes the lifetime cost of a heating system over its lifetime.

    Args:
        heating_system (str): heating system.
            Takes "ashp" (for air source heat pump) or "boiler" (for gas boiler).
        archetype (str): Property archetype
            Takes: TODO: add final list of archetypes.
        annual_cost_reduction (float): how much the cost of installing the heating system reduces each year
            in comparison to the previous year.
        installation_year (int): the year in which the heating system is installed.
        annual_maintenance_costs (float): The annual maintenance cost of the heating system.
        life_span (int): Number of years the heating system is assumed to be operational.
        decile (int, optional): cost decile, only used for air source heat pumps.
        subsidy_model_or_value (str): The subsidy model to get the subsidy to be subtracted
            OR a fixed subsidy value.
            Models include: "flat", "slow stepdown", "fast stepdown", "high", "zero from 2028",
            "smallest", "no subsidy".

    Raises:
        ValueError: If the subsidy model is not applicable for the heating system.

    Returns:
        float: The total costs over the specified number of years.
    """
    if (heating_system != "ashp") and (subsidy_model_or_value in config.get("ashp_subsidy_options")):
        raise ValueError("Subsidy model is only applicable for air source heat pumps. Please provide a number.")

    upfront_cost = compute_upfront_cost(
        heating_system=heating_system,
        archetype=archetype,
        decile=decile,
        annual_cost_reduction=annual_cost_reduction,
        installation_year=installation_year,
        subsidy_model_or_value=subsidy_model_or_value,
    )
    maintenance_cost = compute_total_maintenance_cost(
        annual_maintenance_costs=annual_maintenance_costs, life_span=life_span
    )

    # running_costs = compute_running_costs()

    return upfront_cost + maintenance_cost


def create_cost_breakdown_per_year_in_lifetime(cost_value: float, life_span: int, installation_year: int) -> dict:
    """Creates a breakdown of costs per year in the lifetime of the heating system.

    Args:
        cost_value (float): The total cost value to be broken down.
        life_span (int): Number of years the heating system is assumed to be operational.
        installation_year (int): The year in which the heating system is installed.

    Returns:
        dict: A dictionary with years as keys and cost values as values.
    """
    cost_per_year = cost_value / life_span
    cost_breakdown = dict.fromkeys(
        range(installation_year, installation_year + life_span),
        cost_per_year,
    )

    return cost_breakdown
