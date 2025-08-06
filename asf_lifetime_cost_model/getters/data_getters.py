"""Data getters for inputs into lifetime cost calculations including:
- air source heat pump installation costs
- annual heat demand for property archetype
- DESNZ gas and electricity wholesale price projections (2023-2050)
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
    _read_excel_to_dataframe,
)


def get_ashp_installation_costs() -> pd.DataFrame:
    """
    Get dataframe of air-source heat pump installations costs from S3.

    Returns:
        pd.DataFrame: Dataframe of air-source heat pump installation costs for each decile in different property archetypes.
    """
    return _read_s3_csv_to_dataframe(
        bucket_name="asf-lifetime-cost-model",
        s3_key="inputs/ashp_installation_costs.csv",
    )


def get_property_heat_demand() -> pd.DataFrame:
    """
    Get dataframe of average heat demand data from S3.

    Returns:
        pd.DataFrame: Dataframe of average heat demand for each decile in different property archetypes. Deciles are based on ashp installation costs.
    """
    return _read_s3_csv_to_dataframe(
        bucket_name="asf-lifetime-cost-model", s3_key="inputs/property_heat_demand.csv"
    )


def get_desnz_wholesale_price_projections(
    projection_scenario_names: list[str],
) -> pd.DataFrame:
    """
    Get dataframe containing DESNZ wholesale price projections for natural gas and electricity from 2001 to 2050 under different scenarios.

    Possible scenarios include:
    - "reference"
    - "low fossil fuel prices" (reference assumptions with lower fossil fuel prices)
    - "high fossil fuel prices" (reference assumptions with higher fossil fuel prices)
    - "low economic growth" (reference assumptions with lower economic growth)
    - "high economic growth" (reference assumptions with higher economic growth)
    - "existing policies only" (reference assumptions, but excluding planned policies)

    Args:
        projection_scenario_names (list[str]): List of scenario names of interest, valid scenario names as listed above.

    Returns:
        pd.DataFrame: Dataframe containing time-series data for price projections for natural gas and electricity.
    """

    # Read all sheets in Excel workbook into a dictionary from website
    all_sheets = _read_excel_to_dataframe(
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

    # Extract tables for each projection scenario specified
    projection_scenarios = {}
    for scenario in projection_scenario_names:

        # Select tab of interest
        df = all_sheets.get(scenario_name_map.get(scenario))

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
        df["projection scenario"] = scenario

        projection_scenarios[scenario] = df

    # Combine individual scenario tables into one dataframe
    combined_projection_scenarios = pd.concat(
        projection_scenarios.values(), ignore_index=True
    )

    return combined_projection_scenarios


def get_tariffs(payment_method: str, price_cap_period: str) -> Tuple[Tariff, Tariff]:
    """
    Create gas and electricity Tariff objects from Ofgem price cap data (Annex 9 file).
    A Tariff object is a representation of the rates that are charged against energy consumption.
    Attributes include fuel type and price cap period interval, and also hold values of each
    cost component that contributes to the total cost of energy as a standing charge and as a unit cost.
    See full documentation at: https://github.com/nestauk/asf_levies_model/blob/dev/asf_levies_model/tariffs.py

    Args:
        payment_method (str): Payment method of interest, valid arguments are: Other Payment Method, PPM, Standard Credit.
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
        payment_method (str, optional): Payment method of interest, valid arguments are: Other Payment Method, PPM, Standard Credit. Defaults to "Other Payment Method".

    Returns:
        Tuple[Tariff, Tariff]: Gas Tariff and electricity Tariff objects corresponding to payment method for current price cap.
    """
    current_price_cap_period = datetime.now().strftime("%Y-%m-%d")

    gas_tariff, electricity_tariff = get_tariffs(
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

    # Total domestic energy consumption and energy customer numbers from DESNZ subnational consumption domestic data, 2023
    # These are to provide consistent charging bases across all levies when rebalancing
    # Source: https://www.gov.uk/government/statistics/regional-and-local-authority-gas-consumption-statistics
    # Source: https://www.gov.uk/government/statistics/regional-and-local-authority-electricity-consumption-statistics
    supply_elec = 96_517_461  # total domestic electricity consumption in MWh, GB
    supply_gas = (
        266_505_188  # total domestic gas consumption in MWh, GB, non-weather corrected
    )
    customers_gas = 24_605_467  # number of domestic gas meters, GB
    customers_elec = 29_239_936  # number of domestic electricity meters, GB

    # Store in dictionary
    denominator_values = {
        "supply_elec": supply_elec,
        "supply_gas": supply_gas,
        "customers_gas": customers_gas,
        "customers_elec": customers_elec,
    }

    # Scaling factor for estimating domestic share of Feed-in Tariff revenue based on total GB electricity supply and exempt supply for Energy Intensive Industries
    total_supply_elec = 249_044_438  # DESNZ GB total electricity consumption, 2023, all consumption (domestic and non-domestic)
    exempt_eii_supply = (
        10_529_633  # Apr-Jun2025 period, Annex 4, New FIT methodology tab
    )
    fit_scaling_factor = supply_elec / (total_supply_elec - exempt_eii_supply)

    # Scaling factor for estimating domestic share of Network Charging Compensation revenue
    ncc_eligible_supply = (
        119_380_310.7  # Mar-Jun2025 period, Annex 4, NCC methodology tab
    )
    ncc_scaling_factor = supply_elec / ncc_eligible_supply

    # Instantiate LevyCollection
    fileobject = levies_data_getters.download_annex_4(as_fileobject=True)
    list_levies = [
        levies.RO.from_dataframe(
            levies_data_getters.process_data_RO(fileobject),
            denominator=supply_elec,
            price_cap=price_cap_period,
        ),
        levies.AAHEDC.from_dataframe(
            levies_data_getters.process_data_AAHEDC(fileobject),
            denominator=supply_elec,
            price_cap=price_cap_period,
        ),
        levies.GGL.from_dataframe(
            levies_data_getters.process_data_GGL(fileobject),
            denominator=customers_gas,
            price_cap=price_cap_period,
        ),
        levies.WHD.from_dataframe(
            levies_data_getters.process_data_WHD(fileobject),
            customers_gas=customers_gas,
            customers_elec=customers_elec,
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
        levies.NCC.from_dataframe(
            levies_data_getters.process_data_NCC(fileobject),
            scaling_factor=ncc_scaling_factor,
            price_cap=price_cap_period,
        ),
    ]
    fileobject.close()

    levy_collection = levies.LevyCollection(
        "Policy Costs", "pc", list_levies, denominator_values
    )

    return levy_collection


def get_rebalanced_levies(
    scenario_name: str, price_cap_period: str = "LATEST"
) -> LevyCollection:
    """
    Create a LevyCollection containing Levy objects that have been rebalanced according to the scenario provided.

    Args:
        scenario_name (str): Rebalancing scenario, valid arguments are "Remove all", "Rebalance RO and FiT to gas", "Remove from electricity", "Rebalance electricity unit cost levies to gas", "Rebalance all to gas".
        price_cap_period (str, optional): Date of interest in YYYY-MM-DD format. "LATEST" is also valid to get the most recently available price cap.. Defaults to "LATEST".

    Raises:
        KeyError: If unrecognised scenario is provided.

    Returns:
        LevyCollection: LevyCollection object containing rebalanced Levy objects, each representing a levy present in the policy costs component of the price cap period provided.
    """

    """
    Rebalance levies according to supplied denominators (consumption and customer charging base). Note: This is used for internal consistency in rebalancing as different charging base numbers are used across different levies to determine levy rates.
    """
    # Instanatiate current levies
    levy_collection_for_rebalancing = get_levies(
        price_cap_period=price_cap_period
    ).rebalance_to_denominators()

    # Instantiate a dictionary that holds electricity/gas and variable/fixed revenue weights for each levy
    # These weights will be modified in the rebalancing process
    rebalancing_weights = create_scenario_weights_dict(levy_collection_for_rebalancing)

    # Scenario: Remove all levies
    if scenario_name == "remove all":
        for levy in levy_collection_for_rebalancing:
            rebalancing_weights[levy.short_name] = {
                "new_electricity_weight": 0,
                "new_gas_weight": 0,
                "new_tax_weight": 1,
                "new_variable_weight_elec": 0,
                "new_fixed_weight_elec": 0,
                "new_variable_weight_gas": 0,
                "new_fixed_weight_gas": 0,
            }

    # Scenario: Rebalance RO and FiT to gas (partial rebalancing)
    elif scenario_name == "rebalance RO and FiT to gas":
        for levy in levy_collection_for_rebalancing[["ro", "fit"]]:
            rebalancing_weights[levy.short_name] = {
                "new_electricity_weight": 0,
                "new_gas_weight": 1,
                "new_tax_weight": 0,
                "new_variable_weight_elec": 0,
                "new_fixed_weight_elec": 0,
                "new_variable_weight_gas": levy.electricity_variable_weight,
                "new_fixed_weight_gas": levy.electricity_fixed_weight,
            }

    # Scenario: Remove all levies from electricity
    elif scenario_name == "remove from electricity":
        for levy in [
            levy
            for levy in levy_collection_for_rebalancing
            if levy.electricity_weight > 0
        ]:
            rebalancing_weights[levy.short_name] = {
                "new_electricity_weight": 0,
                "new_gas_weight": levy.gas_weight,
                "new_tax_weight": levy.electricity_weight,
                "new_variable_weight_elec": 0,
                "new_fixed_weight_elec": 0,
                "new_variable_weight_gas": levy.gas_variable_weight,
                "new_fixed_weight_gas": levy.gas_fixed_weight,
            }

    # Scenario: Rebalance electricity unit cost levies to gas
    elif scenario_name == "rebalance electricity unit cost levies to gas":
        for levy in [
            levy
            for levy in levy_collection_for_rebalancing
            if levy.electricity_variable_weight > 0
        ]:
            rebalancing_weights[levy.short_name] = {
                "new_electricity_weight": 0,
                "new_gas_weight": 1,
                "new_tax_weight": 0,
                "new_variable_weight_elec": 0,
                "new_fixed_weight_elec": 0,
                "new_variable_weight_gas": 1,  # assumes no hybrid of unit cost/standing charge
                "new_fixed_weight_gas": 0,  # assumes no hybrid of unit cost/standing charge
            }

    # Scenario: Rebalance all levies to gas
    elif scenario_name == "rebalance all to gas":
        for levy in [
            levy
            for levy in levy_collection_for_rebalancing
            if levy.electricity_weight > 0
        ]:
            rebalancing_weights[levy.short_name] = {
                "new_electricity_weight": 0,
                "new_gas_weight": 1,
                "new_tax_weight": 0,
                "new_variable_weight_elec": 0,
                "new_fixed_weight_elec": 0,
                "new_variable_weight_gas": levy.electricity_variable_weight,
                "new_fixed_weight_gas": levy.electricity_fixed_weight,
            }

    else:
        raise KeyError("Unrecognised scenario name.")

    # Apply the rebalancing weights to the LevyCollection
    rebalanced_levy_collection = levy_collection_for_rebalancing.rebalance_levies(
        rebalancing_weights, scenario_name=scenario_name, inplace=False
    )

    return rebalanced_levy_collection
