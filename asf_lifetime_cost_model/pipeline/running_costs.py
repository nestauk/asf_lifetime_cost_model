"""Functions that compute the running cost in each year of operation for a heating system."""

import numpy as np
import pandas as pd

from asf_lifetime_cost_model import config


def get_wholesale_price_projection_series(
    wholesale_prices_data_all_scenarios: pd.DataFrame, fuel_type: str, projection_scenario: str
) -> pd.DataFrame:
    """Gets a slice of the DESNZ wholesale price projection dataframe.

    This is done by filtering on given fuel type (electricity or gas) and projection scenario name.
    This function also applies price modifications for the "reference", "low fossil fuel prices" and
    "high fossil fuel prices" projection scenarios.

    Args:
        wholesale_prices_data_all_scenarios (pd.DataFrame): DataFrame containing wholesale price projections
            for all scenarios.
        fuel_type (str): Energy fuel type. Valid arguments are "electricity" or "gas".
        projection_scenario (str): Name of DESNZ projection scenario.
            Valid arguments are "reference", "low fossil fuel prices", "high fossil fuel prices".

    Raises:
        ValueError: Error raised if projection scenario name is not recognised.

    Returns:
        pd.DataFrame: DataFrame containing one row of price projection series for
            given fuel type and projection scenario.
    """
    # Slice data for projection scenario of interest only
    wholesale_prices_data = wholesale_prices_data_all_scenarios[
        wholesale_prices_data_all_scenarios["projection_scenario"] == projection_scenario
    ]

    if projection_scenario == "reference":
        # Modify data so that wholesale prices are held constant at 2040 levels from 2041 to 2050 for reference scenario
        wholesale_prices_data.loc[
            wholesale_prices_data["projection_scenario"] == projection_scenario,
            range(2032, 2051),
        ] = wholesale_prices_data.loc[
            wholesale_prices_data["projection_scenario"] == projection_scenario,
            2040,
        ]
    elif (projection_scenario == "low fossil fuel prices") | (projection_scenario == "high fossil fuel prices"):
        # Modify data so that wholesale prices are held constant at 2031 levels from 2032 to 2050 for low and
        # high fossil fuel prices scenarios
        wholesale_prices_data.loc[
            :,
            range(2032, 2051),
        ] = wholesale_prices_data.loc[
            :,
            2031,
        ]
    else:
        supported = (
            "Supported projection scenarios are: 'reference', 'low fossil fuel prices', 'high fossil fuel prices'."
        )
        raise ValueError(f"Unsupported projection scenario name: {projection_scenario}. {supported}")

    wholesale_prices_series = wholesale_prices_data[wholesale_prices_data["fuel"].str.contains(fuel_type, case=False)]

    return wholesale_prices_series


def create_energy_cost_time_series(
    tariff_time_series: dict,
    fuel_type: str,
    wholesale_prices_series: pd.DataFrame,
) -> tuple[dict[int, float], dict[int, float]]:
    """Creates two time series of total energy costs (excluding VAT).

    One of the time series is for unit costs and another for standing charges,
    with the wholesale price replaced with the DESNZ projection for each year in the future.

    Args:
        tariff_time_series (dict): Dictionary where keys are years of operation and values are the Tariff object
            for each year.
        fuel_type (str): Fuel type, valid arguments are "electricity" and "gas".
        wholesale_prices_series (pd.DataFrame): DataFrame containing one row of price projection series for
            corresponding fuel type and chosen projection scenario.

    Raises:
        ValueError: Error raised if fuel_type is not recognised.

    Returns:
        tuple[dict[int, float], dict[int, float]]: Tuple containing two dictionaries; the first containing the unit
            cost of energy for each year of operation and the second containing the standing charge of energy for
            each year of operation.
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
