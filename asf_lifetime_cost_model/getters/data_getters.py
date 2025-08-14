"""Data getters for inputs into lifetime cost calculations including:
- inflation adjusted air source heat pump installation costs per decile and property archetype
- annual heat demand for each property archetype
- DESNZ gas and electricity wholesale price projections for natural gas and electricity (2023-2050)
- Ofgem energy price cap
- policy costs after levy rebalancing"""

from typing import Tuple
from datetime import datetime

import asf_levies_model.getters.load_data as levies_data_getters
import asf_levies_model.levies as levies
import asf_levies_model.tariffs as tariffs
import pandas as pd

from asf_levies_model.tariffs import Tariff
from asf_levies_model.levies import LevyCollection
from asf_levies_model.summary import create_scenario_weights_dict

from asf_lifetime_cost_model.getters.getter_utils import (
    _read_s3_csv_to_dataframe,
    _read_excel_to_dataframe_or_dict,
)


def get_ashp_installation_costs() -> pd.DataFrame:
    """
    Get dataframe of inflation-adjusted air-source heat pump installations costs for each decile in different property archetypes from S3.

    Returns:
        pd.DataFrame: Dataframe of air-source heat pump installation costs
    """
    return _read_s3_csv_to_dataframe(
        bucket_name="asf-lifetime-cost-model",
        s3_key="inputs/ashp_installation_costs.csv",
    )


def get_property_heat_demand() -> pd.DataFrame:
    """
    Get dataframe of average heat demand data from S3 for each property archetype.

    Returns:
        pd.DataFrame: Dataframe of average heat demand
    """
    return _read_s3_csv_to_dataframe(
        bucket_name="asf-lifetime-cost-model", s3_key="inputs/property_heat_demand.csv"
    )


def get_desnz_wholesale_price_projections() -> pd.DataFrame:
    """
    Downloads DESNZ wholesale price projections and creates dataframe containing price projections for natural gas and electricity from 2001 to 2050 (inflation-adjusted to 2023 prices) under different scenarios.

    The resulting DataFrame contains one column per year (with price data) and columns containing additional information such as: metric, fuel, units and projection_scenario

    Scenarios for which data is available include:
    - "reference"
    - "low fossil fuel prices" (reference assumptions with lower fossil fuel prices)
    - "high fossil fuel prices" (reference assumptions with higher fossil fuel prices)
    - "low economic growth" (reference assumptions with lower economic growth)
    - "high economic growth" (reference assumptions with higher economic growth)
    - "existing policies only" (reference assumptions, but excluding planned policies)


    Returns:
        pd.DataFrame: Dataframe containing time-series data for price projections for natural gas and electricity.
    """

    # Read all sheets in Excel workbook into a dictionary from website
    all_sheets = _read_excel_to_dataframe_or_dict(
        "https://assets.publishing.service.gov.uk/media/6751eae76da7a3435fecbd8e/Annex_M_assumptions_growth_price.ods"
    )

    # Mapping our scenario names to DESNZ scenario tab names
    scenario_name_map = {
        "reference": "Reference",
        "low fossil fuel prices": "FFP_Low",
        "high fossil fuel prices": "FFP_High",
        "low economic growth": "GDP_Low",
        "high economic growth": "GDP_High",
        "existing policies only": "Existing",
    }

    # Extract tables for each projection scenario
    projection_scenarios = {}
    for scenario_name, scenario_tab_name in scenario_name_map.items():
        # Select tab of interest
        df = all_sheets.get(scenario_tab_name)

        # Header row
        df.columns = df.iloc[1]

        # Filter for rows of interest
        df = df[
            (df["fuel"] == "Electricity (volume weighted)")
            | (df["fuel"] == "Natural gas")
        ].reset_index(drop=True)

        # Drop redundant columns
        df = df.drop(["coverage", "note"], axis=1)

        # Look up scenario name to add to dataframe
        df["projection_scenario"] = scenario_name

        projection_scenarios[scenario_name] = df

    # Combine individual scenario tables into one dataframe
    combined_projection_scenarios = pd.concat(
        projection_scenarios.values(), ignore_index=True
    )

    return combined_projection_scenarios


def _create_tariff_objects(
    payment_method: str, price_cap_period: str
) -> Tuple[Tariff, Tariff]:
    """
    Downloads Ofgem price cap data (Annex 9 file) and creates gas and electricity Tariff objects.

    A Tariff object is a representation of the rates that are charged against energy consumption.
    Each tariff object includes attributes such as fuel type and price cap period interval, also holding values of each
    cost component that contributes to the total cost of energy as a standing charge and as a unit cost.
    See full documentation at: https://github.com/nestauk/asf_levies_model/blob/dev/asf_levies_model/tariffs.py

    Args:
        payment_method (str): Payment method of interest, valid arguments are: 'Other Payment Method', 'PPM', 'Standard Credit'.
        price_cap_period (str): Date of interest in YYYY-MM-DD format. "LATEST" is also valid to get the most recently available price cap.

    Raises:
        KeyError: If provided payment method type is not one of the valid types.

    Returns:
        Tuple[Tariff, Tariff]: Gas Tariff and electricity Tariff objects corresponding to payment method and price cap period provided.
    """

    # Get Annex 9 which contains data on final energy price cap rates
    fileobject = levies_data_getters.download_annex_9(as_fileobject=True)

    if payment_method == "Other Payment Method":
        gas_tariff = tariffs.GasOtherPayment.from_dataframe(
            levies_data_getters.process_tariff_gas_other_payment_nil(fileobject),
            levies_data_getters.process_tariff_gas_other_payment_typical(fileobject),
            price_cap=price_cap_period,
        )
        electricity_tariff = tariffs.ElectricityOtherPayment.from_dataframe(
            levies_data_getters.process_tariff_elec_other_payment_nil(fileobject),
            levies_data_getters.process_tariff_elec_other_payment_typical(fileobject),
            price_cap=price_cap_period,
        )
    elif payment_method == "PPM":
        gas_tariff = tariffs.GasPPM.from_dataframe(
            levies_data_getters.process_tariff_gas_ppm_nil(fileobject),
            levies_data_getters.process_tariff_gas_ppm_typical(fileobject),
            price_cap=price_cap_period,
        )
        electricity_tariff = tariffs.ElectricityPPM.from_dataframe(
            levies_data_getters.process_tariff_elec_ppm_nil(fileobject),
            levies_data_getters.process_tariff_elec_ppm_typical(fileobject),
            price_cap=price_cap_period,
        )
    elif payment_method == "Standard Credit":
        gas_tariff = tariffs.GasStandardCredit.from_dataframe(
            levies_data_getters.process_tariff_gas_standard_credit_nil(fileobject),
            levies_data_getters.process_tariff_gas_standard_credit_typical(fileobject),
            price_cap=price_cap_period,
        )
        electricity_tariff = tariffs.ElectricityStandardCredit.from_dataframe(
            levies_data_getters.process_tariff_elec_standard_credit_nil(fileobject),
            levies_data_getters.process_tariff_elec_standard_credit_typical(fileobject),
            price_cap=price_cap_period,
        )

    else:
        raise KeyError(
            "Please provide a valid payment method (Other Payment Method, PPM or Standard Credit.)"
        )

    fileobject.close()

    return gas_tariff, electricity_tariff


def get_current_energy_price_cap_tariffs(
    payment_method: str = "Other Payment Method",
) -> Tuple[Tariff, Tariff]:
    """
    Create gas and electricity Tariff objects from Ofgem price cap data.

    Args:
        payment_method (str, optional): Payment method of interest, valid arguments are: 'Other Payment Method', 'PPM', 'Standard Credit'. Defaults to "Other Payment Method".

    Returns:
        Tuple[Tariff, Tariff]: Gas Tariff and electricity Tariff objects corresponding to payment method for current price cap.
    """
    current_price_cap_period = datetime.now().strftime("%Y-%m-%d")

    gas_tariff, electricity_tariff = _create_tariff_objects(
        payment_method=payment_method, price_cap_period=current_price_cap_period
    )

    return gas_tariff, electricity_tariff


def get_levies(price_cap_period: str) -> LevyCollection:
    """
    Create LevyCollection object containing Levy objects representing policy costs for the price cap period provided.

    Args:
        price_cap_period (str): Date of interest in YYYY-MM-DD format."LATEST" is also valid to get the most recently available price cap.

    Returns:
        LevyCollection: LevyCollection object containing all Levy objects, each representing a levy present in the policy costs component of the price cap period provided.
    """

    # Definining parameters that are required for levy rebalancing calculations

    # Total domestic energy consumption and energy customer numbers from DESNZ subnational consumption domestic data, 2023 - TO MOVE TO CONFIG
    # These are to provide consistent charging bases across all levies when rebalancing
    # Source: https://www.gov.uk/government/statistics/regional-and-local-authority-gas-consumption-statistics
    # Source: https://www.gov.uk/government/statistics/regional-and-local-authority-electricity-consumption-statistics
    domestic_supply_electricity = (
        96_517_461  # total domestic electricity consumption in MWh, GB
    )
    domestic_supply_gas = (
        266_505_188  # total domestic gas consumption in MWh, GB, non-weather corrected
    )
    domestic_customers_gas = 24_605_467  # number of domestic gas meters, GB
    domestic_customers_electricity = (
        29_239_936  # number of domestic electricity meters, GB
    )
    total_supply_electricity = 249_044_438  # DESNZ GB total electricity consumption, 2023, all consumption (domestic and non-domestic)

    # Store in dictionary
    denominator_values = {
        "supply_elec": domestic_supply_electricity,
        "supply_gas": domestic_supply_gas,
        "customers_gas": domestic_customers_gas,
        "customers_elec": domestic_customers_electricity,
    }

    # Get Ofgem Annex 4 Policy Cost model file
    fileobject = levies_data_getters.download_annex_4(as_fileobject=True)

    # Calculate scaling factor for estimating domestic share of Feed-in Tariff (FIT) revenue based on total GB electricity supply and exempt supply for Energy Intensive Industries (EII)
    fit_levy = levies.FIT.from_dataframe(
        levies_data_getters.process_data_FIT(fileobject),
        price_cap=price_cap_period,
    )
    fit_exempt_eii_supply = fit_levy.ExemptSupplyEII
    fit_scaling_factor = domestic_supply_electricity / (
        total_supply_electricity - fit_exempt_eii_supply
    )

    # Calculate scaling factor for estimating domestic share of Network Charging Compensation (NCC) revenue
    ncc_levy = levies.NCC.from_dataframe(
        levies_data_getters.process_data_NCC(fileobject),
        price_cap=price_cap_period,
    )
    ncc_eligible_supply = ncc_levy.EligibleDemand
    ncc_scaling_factor = domestic_supply_electricity / ncc_eligible_supply

    # Instantiate levies in LevyCollection
    list_levies = [
        levies.RO.from_dataframe(
            levies_data_getters.process_data_RO(fileobject),
            denominator=domestic_supply_electricity,
            price_cap=price_cap_period,
        ),
        levies.AAHEDC.from_dataframe(
            levies_data_getters.process_data_AAHEDC(fileobject),
            denominator=domestic_supply_electricity,
            price_cap=price_cap_period,
        ),
        levies.GGL.from_dataframe(
            levies_data_getters.process_data_GGL(fileobject),
            denominator=domestic_customers_gas,
            price_cap=price_cap_period,
        ),
        levies.WHD.from_dataframe(
            levies_data_getters.process_data_WHD(fileobject),
            customers_gas=domestic_customers_gas,
            customers_elec=domestic_customers_electricity,
            price_cap=price_cap_period,
        ),
        levies.ECO4.from_dataframe(
            levies_data_getters.process_data_ECO(fileobject), price_cap=price_cap_period
        ),  # Split ECO
        levies.GBIS.from_dataframe(
            levies_data_getters.process_data_ECO(fileobject), price_cap=price_cap_period
        ),  # Split ECO
        levies.FIT.from_dataframe(
            levies_data_getters.process_data_FIT(fileobject),
            scaling_factor=fit_scaling_factor,
            price_cap=price_cap_period,
        ),
    ]

    # NCC is a levy that was introduced in price cap period Apr2025-Sep2025
    # If price cap period of interest is before this, the NCC levy introduces nan values
    # that creates problems for LevyCollection calculations
    # Check if NCC has nan revenue
    ncc_levy = levies.NCC.from_dataframe(
        levies_data_getters.process_data_NCC(fileobject),
        scaling_factor=ncc_scaling_factor,
        price_cap=price_cap_period,
    )
    if not pd.isna(ncc_levy.revenue):
        list_levies.append(ncc_levy)

    fileobject.close()

    levy_collection = levies.LevyCollection(
        "Policy Costs", "pc", list_levies, denominator_values
    )

    return levy_collection


def get_rebalanced_levies(
    levies_to_rebalance: list[str],
    electricity_weight: float,
    gas_weight: float,
    tax_weight: float,
    variable_electricity_weight: float,
    fixed_electricity_weight: float,
    variable_gas_weight: float,
    fixed_gas_weight: float,
    price_cap_period: str = "LATEST",
) -> LevyCollection:
    """
    Creates a LevyCollection where a given set of levies are rebalanced using the same rebalancing weights.

    Args:
        levies_to_rebalance (list[str]): list containing short names of levies to be rebalanced with provided weights.
        electricity_weight (float): [0, 1] indicating electricity proportion of levy revenue.
            0 means that 0% of the total revenue of the policy scheme is levied on electricity bills.
            1 means that 100% of the total revenue of the policy scheme is levied on electricity bills.
        gas_weight (float): [0, 1] indicating gas proportion of levy revenue.
            0 means that 0% of the total revenue of the policy scheme is levied on gas bills.
            1 means that 100% of the total revenue of the policy scheme is levied on gas bills.
        tax_weight (float): [0, 1] indicating general taxation proportion of levy revenue.
            0 means that 0% of the total revenue of the policy scheme is funded through general taxation (not on energy bills at all).
            1 means that 100% of the total revenue of the policy scheme is funded through general taxation (not on energy bills at all).
        variable_electricity_weight (float): [0, 1] indicating the proportion of electricity revenue that is variable (e.g. per unit consumption).
            0 means that 0% of the total revenue of the policy scheme to be raised through electricity bills is levied against electricity units.
            1 means that 100% of the total revenue of the policy scheme to be raised through electricity bills is levied against electricity units.
        fixed_electricity_weight (float): [0, 1] indicating the proportion of electricity revenue that is fixed (e.g. per customer).
            0 means that 0% of the total revenue of the policy scheme to be raised through electricity bills is levied as a standing charge (per electricity customer basis).
            1 means that 100% of the total revenue of the policy scheme to be raised through electricity bills is levied as a standing charge (per electricity customer basis).
        variable_gas_weight (float): [0, 1] indicating the proportion of gas revenue that is variable (e.g. per unit consumption).
            0 means that 0% of the total revenue of the policy scheme to be raised through gas bills is levied against gas units.
            1 means that 100% of the total revenue of the policy scheme to be raised through gas bills is levied against gas units.
        fixed_gas_weight (float): [0, 1] indicating the proportion of gas revenue that is fixed (e.g. per customer).
            0 means that 0% of the total revenue of the policy scheme to be raised through gas bills is levied as a standing charge (per gas customer basis).
            1 means that 100% of the total revenue of the policy scheme to be raised through gas bills is levied as a standing charge (per gas customer basis).
        price_cap_period (str, optional): Date of interest in YYYY-MM-DD format. Defaults to "LATEST" to get the most recently available price cap.

    Returns:
        LevyCollection: LevyCollection object containing rebalanced Levy objects, each representing a levy present in the policy costs component of the price cap period provided.
    """

    # Rebalance levies according to supplied denominators (consumption and customer charging base).
    # Note: This is used for internal consistency in rebalancing as different charging base numbers are used across different levies to determine levy rates.
    levy_collection_for_rebalancing = get_levies(
        price_cap_period=price_cap_period
    ).rebalance_to_denominators()

    # Instantiate a dictionary that hold current electricity/gas and variable/fixed revenue weights for each levy
    # These weights will be modified in the rebalancing process
    rebalancing_weights = create_scenario_weights_dict(levy_collection_for_rebalancing)

    for short_name in levies_to_rebalance:
        rebalancing_weights[short_name] = {
            "new_electricity_weight": electricity_weight,
            "new_gas_weight": gas_weight,
            "new_tax_weight": tax_weight,
            "new_variable_weight_elec": variable_electricity_weight,
            "new_fixed_weight_elec": fixed_electricity_weight,
            "new_variable_weight_gas": variable_gas_weight,
            "new_fixed_weight_gas": fixed_gas_weight,
        }

    # Apply the rebalancing weights to the LevyCollection
    rebalanced_levy_collection = levy_collection_for_rebalancing.rebalance_levies(
        rebalancing_weights, scenario_name="Rebalancing scenario", inplace=False
    )

    return rebalanced_levy_collection
