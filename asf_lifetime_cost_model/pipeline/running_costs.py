"""
Functions that compute the running cost in each year of operation for a heating system
"""

import pandas as pd
import numpy as np

from typing import Optional

from asf_lifetime_cost_model import config
import asf_lifetime_cost_model.getters.data_getters as data_getters


def get_property_heat_demand(archetype: str) -> float:
    """
    Extracts annual heat demand value for a given property archetype.

    Args:
        archetype (str): Name of property archetype. Valid arguments are TO-DO.

    Raises:
        ValueError: Error raised if property archetype name is not recognised.

    Returns:
        float: Average annual heat demand of property archetype.
    """

    # Get property heat demand data
    heat_demand_data = data_getters.get_property_heat_demand()

    archetypes = list(heat_demand_data["archetype_label"])

    # If unrecognised archetype is provided
    if archetype not in archetypes:
        raise ValueError(f"Unsupported property archetype: {archetype}. Supported archetypes are: {archetypes}")

    # Extract annual heat demand of selected property archetype
    property_heat_demand = heat_demand_data.loc[heat_demand_data["archetype_label"] == archetype, "heat_demand"].iloc[
        0
    ]  # kWh/year

    return property_heat_demand


def get_wholesale_price_projection_series(fuel_type: str, projection_scenario: str) -> pd.DataFrame:
    """
    Gets a slice of the DESNZ wholesale price projection dataframe by filtering on given fuel type (electricity or gas) and projection scenario name.
    This function also applies price modifications for the "reference", "low fossil fuel prices" and
    "high fossil fuel prices" projection scenarios.

    Args:
        fuel_type (str): Energy fuel type. Valid arguments are "electricity" or "gas".
        projection_scenario (str): Name of DESNZ projection scenario.
            Valid arguments are "reference", "low fossil fuel prices", "high fossil fuel prices".

    Raises:
        ValueError: Error raised if projection scenario name is not recognised.

    Returns:
        pd.DataFrame: DataFrame containing one row of price projection series for given fuel type and projection scenario.
    """

    # Get DESNZ gas and electricity wholesale price projections data
    wholesale_prices_data_all_scenarios = data_getters.get_desnz_wholesale_price_projections()

    # Slice data for projection scenario of interest only
    wholesale_prices_data = wholesale_prices_data_all_scenarios[
        wholesale_prices_data_all_scenarios["projection_scenario"] == projection_scenario
    ]

    if projection_scenario == "reference":
        # Modify data so that wholesale prices are held constant at 2040 levels from 2041 to 2050 for reference scenario
        for year in range(2041, 2051):
            wholesale_prices_data.loc[
                wholesale_prices_data["projection_scenario"] == projection_scenario,
                year,
            ] = wholesale_prices_data.loc[
                wholesale_prices_data["projection_scenario"] == projection_scenario,
                2040,
            ]
    elif (projection_scenario == "low fossil fuel prices") | (projection_scenario == "high fossil fuel prices"):
        # Modify data so that wholesale prices are held constant at 2031 levels from 2032 to 2050 for low and high fossil fuel prices scenarios
        for year in range(2032, 2051):
            wholesale_prices_data.loc[
                wholesale_prices_data["projection_scenario"] == projection_scenario,
                year,
            ] = wholesale_prices_data.loc[
                wholesale_prices_data["projection_scenario"] == projection_scenario,
                2031,
            ]
    else:
        raise ValueError(
            f"Unsupported projection scenario name: {projection_scenario}. Supported projection scenarios are: 'reference', 'low fossil fuel prices', 'high fossil fuel prices'."
        )

    wholesale_prices_series = wholesale_prices_data[wholesale_prices_data["fuel"].str.contains(fuel_type, case=False)]

    return wholesale_prices_series


def create_energy_cost_time_series(
    tariff_time_series: dict,
    fuel_type: str,
    wholesale_prices_series: pd.DataFrame,
) -> tuple[dict[int, float], dict[int, float]]:
    """
    Creates two time series of total energy costs (excluding VAT) in each year of operation (one for unit costs and one for standing charges),
    with the wholesale price replaced with the DESNZ projection for each year in the future.


    Args:
        tariff_time_series (dict): Dictionary where keys are years of operation and values are the Tariff object for each year.
        fuel_type (str): Fuel type, valid arguments are "electricity" and "gas".
        wholesale_prices_series (pd.DataFrame): DataFrame containing one row of price projection series for corresponding fuel type and chosen projection scenario.
            Output of _get_wholesale_price_projection_series().

    Raises:
        ValueError: Error raised if fuel_type is not recognised.

    Returns:
        tuple[dict[int, float], dict[int, float]]: Tuple containing two dictionaries; the first containing the unit cost of energy for each year of operation
            and the second containing the standing charge of energy for each year of operation.
    """

    # Instantiate dictionaries to hold time series
    unit_cost_time_series = {}
    standing_charge_time_series = {}

    for year, tariff in tariff_time_series.items():
        # Cost component to broader category mapping
        tariff_cost_components_category_map = {
            "nil": {
                tariff.df_nil: "wholesale",
                tariff.cm_nil: "wholesale",
                tariff.aa_nil: "other",
                tariff.pc_nil: "policy",
                tariff.nc_nil: "other",
                tariff.oc_nil: "other",
                tariff.smncc_nil: "other",
                tariff.ic_nil: "other",
                tariff.paac_nil: "other",
                tariff.pap_nil: "other",
                tariff.co_nil: "other",
                tariff.drc_nil: "other",
                tariff.ebit_nil: "other",
                tariff.hap_nil: "other",
                tariff.levelisation_nil: "other",
            },
            "variable": {
                tariff.df: "wholesale",
                tariff.cm: "wholesale",
                tariff.aa: "other",
                tariff.pc: "policy",
                tariff.nc: "other",
                tariff.oc: "other",
                tariff.smncc: "other",
                tariff.ic: "other",
                tariff.paac: "other",
                tariff.pap: "other",
                tariff.co: "other",
                tariff.drc: "other",
                tariff.ebit: "other",
                tariff.hap: "other",
                tariff.levelisation: "other",
            },
        }

        # Create dictionary where tariff cost components are aggregated by category
        categories = ["wholesale", "policy", "other"]
        types = [
            "nil",
            "variable",
        ]  # nil for standing charges and variable for unit costs
        tariff_cost_categories = {
            f"{cat} ({type})": np.nansum(
                [
                    component
                    for component, category in tariff_cost_components_category_map.get(type).items()
                    if category == cat
                ]
            )
            for type in types
            for cat in categories
        }

        # Look up wholesale price projection for year
        # But do not replace if year is year of current price cap period
        if year != tariff.price_cap_period.left.year:
            if fuel_type == "gas":
                # Convert p/therm to p/kWh
                therm_to_kwh_conversion = config.get("therm_to_kwh_conversion")

                wholesale_projection = (wholesale_prices_series.loc[:, year].iloc[0]) / therm_to_kwh_conversion  # p/kWh

            elif fuel_type == "electricity":
                wholesale_projection = wholesale_prices_series.loc[:, year].iloc[0]  # p/kWh

            else:
                raise ValueError(f"Unsupported fuel type: {fuel_type}. Supported fuel types are: gas, electricity.")

            # Replace wholesale component with projection
            tariff_cost_categories["wholesale (variable)"] = wholesale_projection * 10  # convert p/kWh to £/MWh

        # Compute total unit cost and standing charge for the year
        unit_cost = np.nansum([value for category, value in tariff_cost_categories.items() if "(variable)" in category])
        standing_charge = np.nansum(
            [value for category, value in tariff_cost_categories.items() if "(nil)" in category]
        )

        # Add year-cost key-value pair to time series dictionary
        unit_cost_time_series[year] = unit_cost
        standing_charge_time_series[year] = standing_charge

    return unit_cost_time_series, standing_charge_time_series


def compute_running_cost_time_series(
    purchase_year: int,
    life_span: int,
    heating_system_efficiency: float,
    fuel_type: str,
    archetype: str,
    wholesale_price_projection_scenario: str,
    include_standing_charge: bool,
    levy_rebalancing: bool,
    levies_to_rebalance: Optional[list[str]] = None,
    levy_rebalancing_weights: Optional[dict[str, float]] = None,
    include_vat: bool = True,
) -> dict[int, float]:
    """
    Creates a time series of total running costs for specified heating system in each year of operation.

    Args:
        purchase_year (int): Year of purchase (i.e. installation), valid arguments are [2025, 2035].
        life_span (int): Number of years assumed to be operational.
        heating_system_efficiency (float): Assumed efficiency of heating system, expressed as a ratio.
            e.g. 1.0 means 100% efficient, 0.85 means 85% efficient, and
            3.0 means 300% efficient (i.e. the system produces 3 units of heat per 1 unit of input energy).
        fuel_type (str): Fuel type, valid arguments are "electricity" or "gas".
        archetype (str): Name of property archetype. Valid arguments are TO-DO.
        wholesale_price_projection_scenario (str): Name of DESNZ projection scenario.
            Valid arguments are "reference", "low fossil fuel prices", "high fossil fuel prices",
            "low economic growth", "high economic growth", "existing policies only"
        include_standing_charge (bool): Whether annual standing charge should be included in running costs.
        levy_rebalancing (bool): Whether a levy rebalancing scenario is to be applied.
        levies_to_rebalance (Optional[list[str]], optional): List containing short names of levies to be rebalanced with provided weights. Defaults to None.
        levy_rebalancing_weights (Optional[dict[str, float]], optional): Dictionary containing rebalancing weights, where
            keys are "electricity_weight", "gas_weight", "tax_weight", "fixed_electricity_weight",
            "variable_electricity_weight", "fixed_gas_weight" and values are revenue propoertions [0, 1].
            Defaults to None.
        include_vat (bool): Whether 5% VAT is included in energy prices. Defaults to True.

    Returns:
        dict[int, float]: Dictionary where keys are years of operation and values are total running costs (£) in each year.
    """

    ### Get heat and energy demand ###

    # Get annual heat demand of property archetype
    property_heat_demand = get_property_heat_demand(archetype)  # kWh/year

    # Calculate annual energy demand of heating system
    energy_demand = property_heat_demand / heating_system_efficiency

    ### Create energy tariff for each year of operation ###

    # Instantiate Tariff objects for latest price cap
    gas_tariff, electricity_tariff = data_getters.get_current_energy_price_cap_tariffs()

    # Apply levy rebalancing scenario to latest policy costs
    if levy_rebalancing:
        rebalanced_levies = data_getters.get_rebalanced_levies(
            levies_to_rebalance=levies_to_rebalance,
            electricity_weight=levy_rebalancing_weights["electricity_weight"],
            gas_weight=levy_rebalancing_weights["gas_weight"],
            tax_weight=levy_rebalancing_weights["tax_weight"],
            variable_electricity_weight=levy_rebalancing_weights["variable_electricity_weight"],
            fixed_electricity_weight=levy_rebalancing_weights["fixed_electricity_weight"],
            variable_gas_weight=levy_rebalancing_weights["variable_gas_weight"],
            fixed_gas_weight=levy_rebalancing_weights["fixed_gas_weight"],
            price_cap_period="LATEST",
        )
        gas_tariff = gas_tariff.update_policy_costs(rebalanced_levies)
        electricity_tariff = electricity_tariff.update_policy_costs(rebalanced_levies)

    # Create list of operating years
    years_of_operation = list(range(purchase_year, purchase_year + life_span))

    # Create a dictionary of gas and electricity tariffs for each year of operation
    # Note we are using the same tariff for each year in the future
    gas_tariff_time_series = {year: gas_tariff for year in years_of_operation}
    electricity_tariff_time_series = {year: electricity_tariff for year in years_of_operation}

    ### Get wholesale price projections ###

    # Get wholesale price projection time series for fuel and scenario of interest
    wholesale_prices_series_df = get_wholesale_price_projection_series(
        fuel_type=fuel_type, projection_scenario=wholesale_price_projection_scenario
    )

    ### Aggregate tariff cost components to replace wholesale price with projection ###

    # Wholesale costs include DF and CM tariff cost components
    # We need to aggregate the tariff cost components by broader categories to be able to
    # replace the wholesale costs with the projection for that year

    # Gas costs
    gas_unit_cost_time_series, gas_standing_charge_time_series = create_energy_cost_time_series(
        tariff_time_series=gas_tariff_time_series,
        fuel_type="gas",
        wholesale_prices_series=wholesale_prices_series_df,
    )

    # Electricity costs
    electricity_unit_cost_time_series, electricity_standing_charge_time_series = create_energy_cost_time_series(
        tariff_time_series=electricity_tariff_time_series,
        fuel_type="electricity",
        wholesale_prices_series=wholesale_prices_series_df,
    )

    if include_vat:
        for cost_time_series in [
            gas_unit_cost_time_series,
            gas_standing_charge_time_series,
            electricity_unit_cost_time_series,
            electricity_standing_charge_time_series,
        ]:
            for year in cost_time_series:
                cost_time_series[year] *= 1.05

    ### Compute total running cost in each year of operation ###
    running_costs_time_series = {}
    for year in years_of_operation:
        if fuel_type == "gas":
            running_costs_time_series[year] = gas_unit_cost_time_series[year] * (
                energy_demand / 1_000
            )  # convert energy_demand in kWh/year to MWh/year

            if include_standing_charge:
                running_costs_time_series[year] += gas_standing_charge_time_series[year]

        else:  # fuel_type is electricity
            running_costs_time_series[year] = electricity_unit_cost_time_series[year] * (energy_demand / 1_000)

            if include_standing_charge:
                running_costs_time_series[year] += electricity_standing_charge_time_series[year]

    return running_costs_time_series
