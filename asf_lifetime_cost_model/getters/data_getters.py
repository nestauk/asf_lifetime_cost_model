"""Data getters for inputs into lifetime cost calculations."""

import pandas as pd

from asf_lifetime_cost_model.getters.getter_utils import _read_s3_csv_to_dataframe, _read_s3_parquet_to_dataframe


def get_ashp_subsidy_options_data() -> pd.DataFrame:
    """Gets dataframe of air source heat pump subsidy options data from S3.

    There's a column for each year between 2024 and 2035 and each option
    is provided as a row in the dataset. Options include:
        - "flat"
        - "slow stepdown"
        - "fast stepdown"
        - "high"
        - "zero from 2028"
        - "smallest"
        - "no subsidy"
    For each pair of year and option, the value is the amount in GBP for subsidising the cost of getting an air source
    heat pump in that year.

    Returns:
        pd.DataFrame: Dataframe of subsidy options
    """
    return _read_s3_csv_to_dataframe(
        bucket_name="asf-lifetime-cost-model",
        s3_key="inputs/ashp_subsidy_options.csv",
    )


def get_latest_price_cap_rate(fuel: str) -> float:
    """Get the latest price cap rate from S3, in p/kWh.

    Finds the most recently modified .parquet file under the fixed price
    cap prefix, then filters to the given fuel, GB average tariff component,
    and the latest 28AD Charge Restriction Period.

    Args:
        fuel: "gas" or "electricity"

    Returns:
        float: The latest price cap rate, in p/kWh (pence per kilowatt-hour)

    Raises:
        ValueError: If zero or more than one matching row is found
    """
    latest_gold = _read_s3_parquet_to_dataframe(
        bucket_name="asf-mission-data-prod",
        s3_key="data/gold/energy_price_cap_levels/annex_9/latest/tariff_component_rates/tariff_component_rates.parquet",
    )

    fuel_value = "Gas" if fuel == "gas" else "Electricity: Single-Rate Metering Arrangement"

    filtered = latest_gold[
        (latest_gold["Fuel"] == fuel_value)
        & (latest_gold["Tariff component"] == "Total_GB average")
        & (latest_gold["Payment method"] == "Other Payment Method")
        & (latest_gold["Type"] == "Unit price")
        & (latest_gold["Unit"] == "p/kWh")
    ]

    latest_period_end = filtered["28AD Charge Restriction Period end"].max()
    result = filtered[filtered["28AD Charge Restriction Period end"] == latest_period_end]["value"]

    if len(result) != 1:
        raise ValueError(f"Expected exactly 1 matching row for fuel={fuel!r}, found {len(result)}")

    return float(result.iloc[0])


def get_latest_price_cap_standing_charge(fuel: str) -> float:
    """Get the latest price cap rate from S3, in p/day.

    Finds the most recently modified .parquet file under the fixed price
    cap prefix, then filters to the given fuel, GB average tariff component,
    and the latest 28AD Charge Restriction Period.

    Args:
        fuel: "gas" or "electricity"

    Returns:
        float: The latest price cap rate, in p/day.

    Raises:
        ValueError: If zero or more than one matching row is found
    """
    latest_gold = _read_s3_parquet_to_dataframe(
        bucket_name="asf-mission-data-prod",
        s3_key="data/gold/energy_price_cap_levels/annex_9/latest/tariff_component_rates/tariff_component_rates.parquet",
    )

    fuel_value = "Gas" if fuel == "gas" else "Electricity: Single-Rate Metering Arrangement"

    filtered = latest_gold[
        (latest_gold["Fuel"] == fuel_value)
        & (latest_gold["Tariff component"] == "Total_GB average")
        & (latest_gold["Payment method"] == "Other Payment Method")
        & (latest_gold["Type"] == "Standing charge")
        & (latest_gold["Unit"] == "p/day")
    ]

    latest_period_end = filtered["28AD Charge Restriction Period end"].max()
    result = filtered[filtered["28AD Charge Restriction Period end"] == latest_period_end]["value"]

    if len(result) != 1:
        raise ValueError(f"Expected exactly 1 matching row for fuel={fuel!r}, found {len(result)}")

    return float(result.iloc[0])
