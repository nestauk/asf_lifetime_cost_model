"""Cost computations.

Functions to handle cost computations for the ASF lifetime cost model including:
- Total maintenance costs
- Upfront installation costs
- Running costs
- Total lifetime costs computation
as a total and as a breakdown per year in the lifetime of the heating system.
"""

# package imports
from typing import List

# local imports
from asf_lifetime_cost_model import config
from asf_lifetime_cost_model.getters import data_getters


def compute_total_maintenance_costs(annual_maintenance_costs: float, life_span: int) -> float:
    """Computes the total amount of maintenance costs given the annual maintenance costs and technology life span.

    Args:
        annual_maintenance_costs (float): The annual maintenance cost of the heating system.
        life_span (int): Number of years assumed to be operational.

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
    """Gets the cost of a heating system based on the archetype, decile, and installation year.

    Args:
        heating_system (str): heating system.
            Takes "ashp" (for air source heat pump) or "boiler" (for gas boiler).
        archetype (str): Household archetype
        decile (int, optional): cost decile, only used for air source heat pumps.

    Raises:
        ValueError: If the heating system inputed is not supported.

    Returns:
        float: The cost of the heating system for the specified archetype (and decile where applicable).
    """
    if heating_system == "ashp":
        costs_data = data_getters.get_ashp_installation_costs()
        cost_value = costs_data[(costs_data["decile"] == decile) & (costs_data["archetype"] == archetype)][
            "cost"
        ].values[0]
    elif heating_system == "boiler":
        costs_data = data_getters.get_gas_boiler_installation_costs()
        cost_value = costs_data[(costs_data["archetype"] == archetype)]["cost"].values[0]
    else:
        raise ValueError(f"Unsupported heating system: {heating_system}")

    return cost_value


def compute_upfront_costs(
    heating_system: str,
    archetype: str,
    annual_cost_reduction: float,
    installation_year: int,
    subtract_subsidy: bool,
    decile: int = None,
    subsidy_model: str = None,
) -> List[float]:
    """Computes the upfront costs of installing a heating system over its life span.

    Args:
        heating_system (str): heating system.
            Takes "ashp" (for air source heat pump) or "boiler" (for gas boiler).
        archetype (str): Household archetype
        decile (int, optional): cost decile, only used for air source heat pumps.
        annual_cost_reduction (float): how much the cost of installing the heating system reduces each year
            in comparison to the previous year.
        installation_year (int): the year in which the heating system is installed.
                    This should be below 2035.
        subtract_subsidy (bool): whether to subtract the subsidy from the upfront costs.
        subsidy_model (str, optional): The model of the subsidy to be subtracted if applicable.

    Raises:
        ValueError: If the heating system inputed is not supported or the year is above or equal to 2035.

    Returns:
        List[float]: A list of upfront costs for each year from the start year to 2035.
    """
    # Get installation cost for a specific heating system, archetype, and decile (where applicable)
    installation_cost = get_installation_cost(heating_system=heating_system, archetype=archetype, decile=decile)

    cost_reduction_data = creates_cost_reduction_data(annual_cost_reduction=annual_cost_reduction)
    cost_reduction_value = cost_reduction_data[installation_year]

    installation_cost = installation_cost * cost_reduction_value

    if subtract_subsidy and heating_system == "ashp":
        # If the heating system is an ASHP and we want to subtract the subsidy, we need to get the subsidy data
        subsidy_data = data_getters.get_subsidy_options_data()
        subsidy_value = subsidy_data[subsidy_data["model"] == subsidy_model]["amount"].values[0]

        return installation_cost - subsidy_value

    return installation_cost


def compute_total_lifetime_costs(
    heating_system: str,
    archetype: str,
    decile: int,
    annual_cost_reduction: float,
    start_year: int,
    subtract_subsidy: bool,
) -> float:
    """Computes the total costs of a heating system over a specified number of years.

    Args:
        heating_system (str): heating system.
            Takes "ashp" (for air source heat pump) or "boiler" (for gas boiler).
        archetype (str): Household archetype
        decile (int): household decile
        annual_cost_reduction (float): how much the cost of installing the heating system reduces each year
            in comparison to the previous year.
        start_year (int): the year in which the heating system is installed.
                    This should be below 2035.
        subtract_subsidy (bool): whether to subtract the subsidy from the upfront costs.

    Returns:
        float: The total costs over the specified number of years.
    """
    upfront_cost = compute_upfront_costs(
        heating_system=heating_system,
        archetype=archetype,
        decile=decile,
        annual_cost_reduction=annual_cost_reduction,
        installation_year=start_year,
        subtract_subsidy=subtract_subsidy,
    )
    maintenance_cost = compute_total_maintenance_costs(heating_system)

    # running_costs = compute_running_costs()

    return upfront_cost + maintenance_cost
