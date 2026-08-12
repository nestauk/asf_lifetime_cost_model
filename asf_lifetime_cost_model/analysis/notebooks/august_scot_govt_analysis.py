# -*- coding: utf-8 -*-
# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     custom_cell_magics: kql
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.11.2
#   kernelspec:
#     display_name: asf_lifetime_cost_model (3.13.2)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Analysis for Scot Govt meeting (Aug 18th 2026)
#
# Requested outputs:
#
# - Annualised lifetime cost comparison gas boiler vs heat pump (breakdown by installation cost, subsidy and running cost)
# - Annual bills for gas boiler vs various heat pump scenarios
# - (Stretch) Target price ratio for various heat pump scenarios

# %%
import pandas as pd

import asf_lifetime_cost_model.getters.data_getters as data_getters
from asf_lifetime_cost_model import config
from asf_lifetime_cost_model.models.heating_system import HeatingSystem
from asf_lifetime_cost_model.models.trajectory import (
    EnergyPriceTrajectory,
    InstallationCostTrajectory,
    SubsidyTrajectory,
)

# %%
# Assumptions
BASE_YEAR = 2026
INFLATION_RATE = config["default_inflation_rate"]  # 2%
DISCOUNT_RATE = config["default_discount_rate"]  # 0.035, HMT Green Book

ASHP_EFFICIENCY = 3.0
ASHP_LIFESPAN = 15
ASHP_REAL_COST_REDUCTION = 0.025  # -2.5%/year real, from_year=2027
ASHP_MAINTENANCE_COST_PER_VISIT = 0  # exclude from this analysis
ASHP_MAINTENANCE_FREQUENCY = 0  # exclude from this analysis

ASHP_HEAT_DEMAND_UPLIFT = 0


ASHP_ELECTRICITY_TOU_TARIFF_DISCOUNT = 0.15  # 15% saving on unit rate, assumed for ASHP owners on a ToU tariff

BOILER_EFFICIENCY = 0.85
BOILER_LIFESPAN = 15
BOILER_INSTALLATION_COST_2026 = 3_000  # £, 2026 real, flat (0% real change)
BOILER_MAINTENANCE_COST_PER_VISIT = 0  # exclude from this analysis
BOILER_MAINTENANCE_FREQUENCY = 0  # exclude from this analysis

MEDIUM_GAS_TDCV = 9_500  # kWh/year
GAS_SHARE_FOR_HEATING = 0.97
MEDIUM_ELECTRICITY_TDCV = 2_500  # kWh/year

ASHP_INSTALLATION_COST_2026 = 12_908  # £, 2026 real
# Median cost of installation A2W heat pump from BUS statistics (Apr-Jun 2026)

# %%
# Energy prices

electricity_prices = EnergyPriceTrajectory(
    fuel="electricity",
    starting_price=data_getters.get_latest_price_cap_rate("electricity"),
    price_basis="real",
    base_year=BASE_YEAR,
)

ashp_electricity_prices = EnergyPriceTrajectory(
    "electricity",
    starting_price=electricity_prices.get_price(year=BASE_YEAR),
    price_basis="real",
    base_year=BASE_YEAR,
)
ashp_electricity_prices.series = electricity_prices.prices.copy()
ashp_electricity_prices.apply_percentage_discount(ASHP_ELECTRICITY_TOU_TARIFF_DISCOUNT)


gas_prices = EnergyPriceTrajectory(
    fuel="gas", starting_price=data_getters.get_latest_price_cap_rate("gas"), price_basis="real", base_year=BASE_YEAR
)

gas_standing_charge = data_getters.get_latest_price_cap_standing_charge(fuel="gas")

# %%
# Installation prices
boiler_installation_costs = InstallationCostTrajectory(
    "gas_boiler",
    starting_cost=BOILER_INSTALLATION_COST_2026,
    price_basis="real",  # 3,000 is already stated in 2026 real £
    base_year=BASE_YEAR,
)

ashp_installation_costs = InstallationCostTrajectory(
    system_type="air_to_water_heat_pump",
    starting_cost=ASHP_INSTALLATION_COST_2026,
    price_basis="real",
    base_year=BASE_YEAR,
)
ashp_installation_costs.set_trajectory(-ASHP_REAL_COST_REDUCTION)

# %%
# Subsidy
ashp_subsidies = SubsidyTrajectory(system_type="air_to_water_heat_pump", starting_subsidy=7_500, price_basis="nominal")
ashp_subsidies.to_real(base_year=BASE_YEAR, inflation_rate=INFLATION_RATE)

ashp_subsidies_zero = SubsidyTrajectory(
    "air_to_water_heat_pump", starting_subsidy=0.0, price_basis="real", base_year=BASE_YEAR
)

gas_boiler_subsidies = SubsidyTrajectory(
    system_type="gas_boiler", starting_subsidy=0.0, price_basis="real", base_year=BASE_YEAR
)

# %%
# Heat demand calculations

heat_demand_with_gas_boiler = (MEDIUM_GAS_TDCV * GAS_SHARE_FOR_HEATING) * BOILER_EFFICIENCY
heat_demand_with_heat_pump = heat_demand_with_gas_boiler * (1 + ASHP_HEAT_DEMAND_UPLIFT)


# %% [markdown]
# Analysis 1. Standard lifetime cost comparison

# %%
# Heat pump (no subsidy) configuration
heat_pump_no_subsidy = HeatingSystem(
    system_type="air_to_water_heat_pump",
    installation_year=BASE_YEAR,
    lifespan=ASHP_LIFESPAN,
    efficiency=ASHP_EFFICIENCY,
    installation_cost_trajectory=ashp_installation_costs,
    subsidy_trajectory=ashp_subsidies_zero,
    maintenance_cost_per_visit=ASHP_MAINTENANCE_COST_PER_VISIT,
    maintenance_annual_frequency=ASHP_MAINTENANCE_FREQUENCY,
)

# %%
# Heat pump configuration
heat_pump = HeatingSystem(
    system_type="air_to_water_heat_pump",
    installation_year=BASE_YEAR,
    lifespan=ASHP_LIFESPAN,
    efficiency=ASHP_EFFICIENCY,
    installation_cost_trajectory=ashp_installation_costs,
    subsidy_trajectory=ashp_subsidies,
    maintenance_cost_per_visit=ASHP_MAINTENANCE_COST_PER_VISIT,
    maintenance_annual_frequency=ASHP_MAINTENANCE_FREQUENCY,
)

# %%
# Gas boiler configuration
gas_boiler = HeatingSystem(
    system_type="gas_boiler",
    installation_year=BASE_YEAR,
    lifespan=BOILER_LIFESPAN,
    efficiency=BOILER_EFFICIENCY,
    installation_cost_trajectory=boiler_installation_costs,
    subsidy_trajectory=gas_boiler_subsidies,
    maintenance_cost_per_visit=BOILER_MAINTENANCE_COST_PER_VISIT,
    maintenance_annual_frequency=BOILER_MAINTENANCE_FREQUENCY,
)

# %%
# Annualised lifetime cost comparison: installation cost, subsidy and running cost breakdown
heat_pump_installation_cost_before_subsidy = (
    heat_pump_no_subsidy.calculate_annualised_discounted_lifetime_capital_cost()
)
heat_pump_installation_cost_net_of_subsidy = heat_pump.calculate_annualised_discounted_lifetime_capital_cost()
heat_pump_subsidy_saving = heat_pump_installation_cost_before_subsidy - heat_pump_installation_cost_net_of_subsidy
heat_pump_running_cost = heat_pump.calculate_annualised_discounted_lifetime_running_cost(
    heat_demand=heat_demand_with_heat_pump, energy_price_trajectory=ashp_electricity_prices
)
heat_pump_total_cost = heat_pump.calculate_annualised_discounted_lifetime_cost(
    heat_demand=heat_demand_with_heat_pump, energy_price_trajectory=ashp_electricity_prices
)

gas_boiler_installation_cost = gas_boiler.calculate_annualised_discounted_lifetime_capital_cost()
gas_boiler_running_cost = gas_boiler.calculate_annualised_discounted_lifetime_running_cost(
    heat_demand=heat_demand_with_gas_boiler, energy_price_trajectory=gas_prices, standing_charge=gas_standing_charge
)
gas_boiler_total_cost = gas_boiler.calculate_annualised_discounted_lifetime_cost(
    heat_demand=heat_demand_with_gas_boiler,
    energy_price_trajectory=gas_prices,
    standing_charge=gas_standing_charge,
)

lifetime_cost_comparison = pd.DataFrame(
    {
        "Heat pump": {
            "Installation cost (before subsidy)": heat_pump_installation_cost_before_subsidy,
            "Subsidy": -heat_pump_subsidy_saving,
            "Installation cost (net of subsidy)": heat_pump_installation_cost_net_of_subsidy,
            "Running cost": heat_pump_running_cost,
            "Total annualised lifetime cost": heat_pump_total_cost,
        },
        "Gas boiler": {
            "Installation cost (before subsidy)": gas_boiler_installation_cost,
            "Subsidy": 0.0,
            "Installation cost (net of subsidy)": gas_boiler_installation_cost,
            "Running cost": gas_boiler_running_cost,
            "Total annualised lifetime cost": gas_boiler_total_cost,
        },
    }
)

lifetime_cost_comparison.map(lambda value: f"£{value:,.2f}/year")

# %% [markdown]
# Analysis 2. Annual bill comparisons

# %%
electricity_price = data_getters.get_latest_price_cap_rate("electricity")  # p/kWh
electricity_standing_charge = data_getters.get_latest_price_cap_standing_charge("electricity")  # p/day
baseline_electricity_bill = (
    MEDIUM_ELECTRICITY_TDCV * (electricity_price / 100)  # usage cost, £/year
    + electricity_standing_charge * 365 / 100  # standing charge, £/year
)

# %%
gas_price_now = data_getters.get_latest_price_cap_rate("gas")
cooking_gas_bill = (MEDIUM_GAS_TDCV * (1 - GAS_SHARE_FOR_HEATING)) * gas_price_now / 100

# %%
# Energy bills with gas boiler for heating and gas for cooking
boiler_gas_bill = gas_boiler.calculate_annualised_discounted_lifetime_running_cost(
    heat_demand=heat_demand_with_gas_boiler,
    energy_price_trajectory=gas_prices,
    standing_charge=gas_standing_charge,
)

boiler_energy_bill = boiler_gas_bill + baseline_electricity_bill + cooking_gas_bill

# %%
# Energy bills with low efficiency heat pump for heating, gas for cooking, standard variable tariff
low_efficiency_heat_pump = HeatingSystem(
    system_type="air_to_water_heat_pump",
    installation_year=BASE_YEAR,
    lifespan=ASHP_LIFESPAN,
    efficiency=2.8,
    installation_cost_trajectory=ashp_installation_costs,
    subsidy_trajectory=ashp_subsidies,
    maintenance_cost_per_visit=ASHP_MAINTENANCE_COST_PER_VISIT,
    maintenance_annual_frequency=ASHP_MAINTENANCE_FREQUENCY,
)

low_efficiency_heat_pump_electricity_bill = (
    low_efficiency_heat_pump.calculate_annualised_discounted_lifetime_running_cost(
        heat_demand=heat_demand_with_heat_pump,
        energy_price_trajectory=electricity_prices,
    )
)

low_efficiency_heat_pump_energy_bill = (
    low_efficiency_heat_pump_electricity_bill
    + baseline_electricity_bill
    + +cooking_gas_bill
    + (gas_standing_charge * 365 / 100)
)

# %%
# Energy bills with high efficiency heat pump for heating, gas for cooking, standard variable tariff
high_efficiency_heat_pump = HeatingSystem(
    system_type="air_to_water_heat_pump",
    installation_year=BASE_YEAR,
    lifespan=ASHP_LIFESPAN,
    efficiency=3.8,
    installation_cost_trajectory=ashp_installation_costs,
    subsidy_trajectory=ashp_subsidies,
    maintenance_cost_per_visit=ASHP_MAINTENANCE_COST_PER_VISIT,
    maintenance_annual_frequency=ASHP_MAINTENANCE_FREQUENCY,
)

high_efficiency_heat_pump_electricity_bill_svt = (
    high_efficiency_heat_pump.calculate_annualised_discounted_lifetime_running_cost(
        heat_demand=heat_demand_with_heat_pump,
        energy_price_trajectory=electricity_prices,
    )
)

high_efficiency_heat_pump_energy_bill_svt = (
    high_efficiency_heat_pump_electricity_bill_svt
    + baseline_electricity_bill
    + cooking_gas_bill
    + (gas_standing_charge * 365 / 100)
)

# %%
# Energy bills with high efficiency heat pump for heating, no gas connection anymore, standard variable tariff
high_efficiency_heat_pump_energy_bill_no_gas_connection_svt = (
    high_efficiency_heat_pump_electricity_bill_svt + baseline_electricity_bill
)

# %%
# Energy bills with high efficiency heat pump for heating, no gas connection anymore, time of use tariff
high_efficiency_heat_pump_electricity_bill_tout = (
    high_efficiency_heat_pump.calculate_annualised_discounted_lifetime_running_cost(
        heat_demand=heat_demand_with_heat_pump,
        energy_price_trajectory=ashp_electricity_prices,
    )
)

high_efficiency_heat_pump_energy_bill_no_gas_connection_tout = (
    high_efficiency_heat_pump_electricity_bill_tout + baseline_electricity_bill
)

# %%
# Annual bill comparison across scenarios
annual_bill_comparison = pd.DataFrame(
    [
        {"Scenario": "Gas boiler (heating) + gas (cooking)", "Annual bill": boiler_energy_bill},
        {
            "Scenario": "Low efficiency heat pump, SVT + gas (cooking)",
            "Annual bill": low_efficiency_heat_pump_energy_bill,
        },
        {
            "Scenario": "High efficiency heat pump, SVT + gas (cooking)",
            "Annual bill": high_efficiency_heat_pump_energy_bill_svt,
        },
        {
            "Scenario": "High efficiency heat pump, SVT, no gas connection",
            "Annual bill": high_efficiency_heat_pump_energy_bill_no_gas_connection_svt,
        },
        {
            "Scenario": "High efficiency heat pump, ToU tariff, no gas connection",
            "Annual bill": high_efficiency_heat_pump_energy_bill_no_gas_connection_tout,
        },
    ]
).set_index("Scenario")

annual_bill_comparison["Saving vs gas boiler"] = boiler_energy_bill - annual_bill_comparison["Annual bill"]

annual_bill_comparison.map(lambda value: f"£{value:,.0f}/year")

# %% [markdown]
# Analysis 3. Solve for target price ratio

# %%
gas_boiler_eac = gas_boiler.calculate_annualised_discounted_lifetime_cost(
    heat_demand_with_gas_boiler,
    gas_prices,
)
gas_boiler_eac

# %%
# Heat pump with SCOP 3.0
required_ashp_electricity_prices = heat_pump.solve_electricity_price_for_parity(
    heat_demand=heat_demand_with_heat_pump,
    energy_price_trajectory=ashp_electricity_prices,
    target_eac=gas_boiler_eac,
)

required_price_cap_rates = {
    year: effective_price / (1 - ASHP_ELECTRICITY_TOU_TARIFF_DISCOUNT)
    for year, effective_price in required_ashp_electricity_prices.items()
}
required_price_cap_rates[2026] / gas_prices.get_price(2026)

# %%
high_efficiency_heat_pump.calculate_annualised_discounted_lifetime_cost(
    heat_demand=heat_demand_with_heat_pump, energy_price_trajectory=ashp_electricity_prices
)

# %%
# Heat pump with SCOP 2.8
required_ashp_electricity_prices = low_efficiency_heat_pump.solve_electricity_price_for_parity(
    heat_demand=heat_demand_with_heat_pump,
    energy_price_trajectory=ashp_electricity_prices,
    target_eac=gas_boiler_eac,
)

required_price_cap_rates = {
    year: effective_price / (1 - ASHP_ELECTRICITY_TOU_TARIFF_DISCOUNT)
    for year, effective_price in required_ashp_electricity_prices.items()
}
required_price_cap_rates[2026] / gas_prices.get_price(2026)

# %%
# Heat pump with SCOP 3.8
required_ashp_electricity_prices = high_efficiency_heat_pump.solve_electricity_price_for_parity(
    heat_demand=heat_demand_with_heat_pump,
    energy_price_trajectory=ashp_electricity_prices,
    target_eac=gas_boiler_eac,
)

required_price_cap_rates = {
    year: effective_price / (1 - ASHP_ELECTRICITY_TOU_TARIFF_DISCOUNT)
    for year, effective_price in required_ashp_electricity_prices.items()
}
required_price_cap_rates[2026] / gas_prices.get_price(2026)

# %%
