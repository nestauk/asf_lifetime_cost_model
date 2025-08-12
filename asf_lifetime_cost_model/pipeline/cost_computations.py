# """Cost computations.

# A module to handle cost computations for the ASF lifetime cost model.
# """

# from typing import List
# from asf_lifetime_cost_model.getters import data_getters
# from asf_lifetime_cost_model import config


# def compute_total_maintenance_costs(heating_system: str) -> float:
#     """Compute the maintenance costs for a given heating system.

#     Args:
#         heating_system (str): heating system.
#             Takes "ashp" (for air source heat pump) or "boiler" (for gas boiler).
#     Returns:
#         float: The total maintenance costs over the specified number of years.
#     """
#     if heating_system in ["ashp", "boiler"]:
#         maintenance_cost_info = config.get("annual_maintenance_cost")[heating_system]
#         annual_maintenance_cost = maintenance_cost_info.get("annual_cost")
#         years = maintenance_cost_info["number_of_years"]
#     else:
#         raise ValueError(f"Unsupported heating system: {heating_system}")

#     return annual_maintenance_cost * years


# def compute_total_maintenance_costs(annual_maintenance_costs: float, number_of_years: int) -> float:
#     """Compute the total amount of maintenance costs  given the annual maintenance costs and number of years.

#     Args:
#         annual_maintenance_costs (float): The annual maintenance cost of the heating system.
#         number_of_years (int): The number of years over which to compute the maintenance costs.
#     Returns:
#         float: The total maintenance costs over the specified number of years.
#     """
#     return annual_maintenance_costs * number_of_years


# def compute_upfront_costs(
#     heating_system: str,
#     archetype: str,
#     decile: int,
#     annual_cost_reduction: float,
#     start_year: int,
#     subtract_subsidy: bool,
# ) -> List[float]:
#     """Computes the upfront costs of installing a heating system over a range of years.

#     Args:
#         heating_system (str): heating system.
#             Takes "ashp" (for air source heat pump) or "boiler" (for gas boiler).
#         archetype (str): Household archetype
#         decile (int): household decile
#         annual_cost_reduction (float): how much the cost of installing the heating system reduces each year
#             in comparison to the previous year.
#         start_year (int): the year in which the heating system is installed.
#                     This should be below 2035.
#         subtract_subsidy (bool): whether to subtract the subsidy from the upfront costs.

#     Raises:
#         ValueError: If the heating system inputed is not supported or the year is above or equal to 2035.

#     Returns:
#         List[float]: A list of upfront costs for each year from the start year to 2035.
#     """

#     years = range(start_year, 2035 + 1, 1)

#     reduction_per_year = [1 for i in years]

#     reduction_per_year = [(1 - annual_cost_reduction) * reduction_per_year[j - 1] for j in len(range(years[1:]))]

#     if heating_system == "ashp":
#         costs_data = data_getters.get_ashp_costs(decile, start_year)
#         cost_value = costs_data[
#             (costs_data["year"] == start_year)
#             & (costs_data["decile"] == decile)
#             & (costs_data["archetype"] == archetype)
#         ]["cost"].values[0]
#     elif heating_system == "boiler":
#         costs_data = data_getters.get_boiler_costs(decile, start_year)
#     else:
#         raise ValueError(f"Unsupported heating system: {heating_system}")

#     cost_per_year = [cost_value * reduction_per_year[i] for i in range(len(reduction_per_year))]

#     if subtract_subsidy:
#         subsidy_data = data_getters.get_subsidy_data(heating_system, start_year)
#         cost_per_year = [cost - subsidy_data for cost in cost_per_year]
#         cost_per_year = [max(0, cost) for cost in cost_per_year]

#     return cost_per_year


# def compute_lifetime_costs(
#     heating_system: str,
#     archetype: str,
#     decile: int,
#     annual_cost_reduction: float,
#     start_year: int,
#     subtract_subsidy: bool,
# ) -> float:
#     """Compute the total costs of a heating system over a specified number of years.

#     Args:
#         heating_system (str): heating system.
#             Takes "ashp" (for air source heat pump) or "boiler" (for gas boiler).
#         archetype (str): Household archetype
#         decile (int): household decile
#         annual_cost_reduction (float): how much the cost of installing the heating system reduces each year
#             in comparison to the previous year.
#         start_year (int): the year in which the heating system is installed.
#                     This should be below 2035.
#         subtract_subsidy (bool): whether to subtract the subsidy from the upfront costs.

#     Returns:
#         float: The total costs over the specified number of years.
#     """

#     upfront_costs = compute_upfront_costs(
#         heating_system=heating_system,
#         archetype=archetype,
#         decile=decile,
#         annual_cost_reduction=annual_cost_reduction,
#         start_year=start_year,
#         subtract_subsidy=subtract_subsidy,
#     )
#     maintenance_costs = compute_total_maintenance_costs(heating_system)

#     running_costs = compute_running_costs()

#     return [maintenance_costs for _ in range(upfront_costs)] + upfront_costs
