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
#     display_name: .venv
#     language: python
#     name: python3
# ---

# %%
import asf_lifetime_cost_model.getters.data_getters as data_getters

# %% [markdown]
# **Heat pump lifetime cost formula**
#
# `ashp_lifetime_cost = (ashp_energy_demand * electricity_price * ashp_lifetime) + (ashp_installation_cost - ashp_subsidy)`
#
# **Boiler lifetime cost formula**
#
# `boiler_lifetime_cost = (boiler_energy_demand * gas_price * boiler_lifetime) + (gas_standing_charge * boiler_lifetime) + (boiler_installation_cost)`
#
# **Analysis steps**
#
# a) Set `ashp_lifetime_cost = boiler_lifetime_cost` (with `ashp_subsidy = 7500`) with `electricity_price` unknown, solve for `electricity_price` and compare to current price of electricity.
#
# b) Repeat above for different values of `ashp_subsidy`.


# %%
# Function to solve for elecitricity_price at lifetime cost parity
def calculate_electricity_price_for_cost_parity(
    ashp_energy_demand,
    ashp_lifetime,
    ashp_installation_cost,
    ashp_subsidy,
    boiler_energy_demand,
    gas_price,
    boiler_lifetime,
    gas_standing_charge,
    boiler_installation_cost,
):

    boiler_lifetime_cost = (
        (boiler_energy_demand * gas_price * boiler_lifetime)  # including VAT
        + (gas_standing_charge * boiler_lifetime)  # including VAT
        + (boiler_installation_cost)
    )

    ashp_upfront_cost = ashp_installation_cost - ashp_subsidy

    electricity_price = (boiler_lifetime_cost - ashp_upfront_cost) / (
        ashp_energy_demand * ashp_lifetime
    )
    return electricity_price  # including VAT


# %%
# Assumptions for energy demand
medium_tdcv_gas = (
    11.5  # Medium Typical Domestic Consumption Value, used for energy price cap, MWh
)
heating_gas_share = 0.97  # share of gas TDCV we are assuming is for heating
boiler_efficiency = 0.85
ashp_efficiency = 3.0

heat_demand = medium_tdcv_gas * heating_gas_share  # MWh
ashp_energy_demand = heat_demand / ashp_efficiency  # MWh
boiler_energy_demand = heat_demand / boiler_efficiency  # MWh

# Assumptions about installation cost
ashp_installation_cost = 12_500  # £ Median cost of ASHP installation from BUS statistics 2025 Q2
boiler_installation_cost = 3_000  # £
current_bus_subsidy = 7_500  # £

# Lifetime assumptions
ashp_lifetime = 15  # years
boiler_lifetime = 15  # years

# %% [markdown]
# Median ASHP installation cost source: https://www.gov.uk/government/statistics/boiler-upgrade-scheme-statistics-july-2025
# - Table Q1.1 under 2025 Q2 Apr to Jun

# %%
# Instantiate Tariff objects for Ofgem current energy price cap July - September 2025
current_gas_tariff, current_electricity_tariff = (
    data_getters.get_current_energy_price_cap_tariffs()
)

# %%
current_electricity_price = (
    current_electricity_tariff.calculate_variable_consumption(consumption=1) * 1.05
)  # £/MWh including VAT
current_gas_price = (
    current_gas_tariff.calculate_variable_consumption(consumption=1) * 1.05
)  # £/MWh including VAT
current_gas_standing_charge = (
    current_gas_tariff.calculate_nil_consumption() * 1.05
)  # £/year including VAT

# %%
current_electricity_price, current_gas_price, current_gas_standing_charge

# %% [markdown]
# BUS subsidy = £7,500

# %%
electricity_price_for_parity = calculate_electricity_price_for_cost_parity(
    ashp_energy_demand=ashp_energy_demand,
    ashp_lifetime=ashp_lifetime,
    ashp_installation_cost=ashp_installation_cost,
    ashp_subsidy=current_bus_subsidy,
    boiler_energy_demand=boiler_energy_demand,
    gas_price=current_gas_price,
    boiler_lifetime=boiler_lifetime,
    gas_standing_charge=current_gas_standing_charge,
    boiler_installation_cost=boiler_installation_cost,
)

# %%
electricity_price_for_parity, current_electricity_price

# %%
electricity_price_for_parity, current_electricity_price

# %%
electricity_price_for_parity / current_electricity_price

# %%
(
    (electricity_price_for_parity - current_electricity_price)
    / current_electricity_price
) * 100

# %% [markdown]
# BUS subsidy = £3,750

# %%
electricity_price_for_parity = calculate_electricity_price_for_cost_parity(
    ashp_energy_demand=ashp_energy_demand,
    ashp_lifetime=ashp_lifetime,
    ashp_installation_cost=ashp_installation_cost,
    ashp_subsidy=current_bus_subsidy / 2,
    boiler_energy_demand=boiler_energy_demand,
    gas_price=current_gas_price,
    boiler_lifetime=boiler_lifetime,
    gas_standing_charge=current_gas_standing_charge,
    boiler_installation_cost=boiler_installation_cost,
)

# %%
electricity_price_for_parity, current_electricity_price

# %%
electricity_price_for_parity / current_electricity_price

# %%
(
    (electricity_price_for_parity - current_electricity_price)
    / current_electricity_price
) * 100

# %% [markdown]
# BUS subsidy = £0

# %%
electricity_price_for_parity = calculate_electricity_price_for_cost_parity(
    ashp_energy_demand=ashp_energy_demand,
    ashp_lifetime=ashp_lifetime,
    ashp_installation_cost=ashp_installation_cost,
    ashp_subsidy=0,
    boiler_energy_demand=boiler_energy_demand,
    gas_price=current_gas_price,
    boiler_lifetime=boiler_lifetime,
    gas_standing_charge=current_gas_standing_charge,
    boiler_installation_cost=boiler_installation_cost,
)

# %%
electricity_price_for_parity, current_electricity_price

# %%
electricity_price_for_parity / current_electricity_price

# %%
(
    (electricity_price_for_parity - current_electricity_price)
    / current_electricity_price
) * 100


# %% [markdown]
# Finding subsidy to reach cost parity given current energy prices

# %%
# Function to solve for ashp_subsidy at lifetime cost parity
def calculate_ashp_subsidy_for_cost_parity(
    ashp_energy_demand,
    electricity_price,
    ashp_lifetime,
    ashp_installation_cost,
    boiler_energy_demand,
    gas_price,
    boiler_lifetime,
    gas_standing_charge,
    boiler_installation_cost,
):

    boiler_lifetime_cost = (
        (boiler_energy_demand * gas_price * boiler_lifetime)  # including VAT
        + (gas_standing_charge * boiler_lifetime)  # including VAT
        + (boiler_installation_cost)
    )

    ashp_running_cost = ashp_energy_demand * electricity_price * ashp_lifetime

    ashp_subsidy = ashp_running_cost + ashp_installation_cost - boiler_lifetime_cost

    return ashp_subsidy


# %%
calculate_ashp_subsidy_for_cost_parity(
    ashp_energy_demand=ashp_energy_demand,
    electricity_price=current_electricity_price,
    ashp_lifetime=ashp_lifetime,
    ashp_installation_cost=ashp_installation_cost,
    boiler_energy_demand=boiler_energy_demand,
    gas_price=current_gas_price,
    boiler_lifetime=boiler_lifetime,
    gas_standing_charge=current_gas_standing_charge,
    boiler_installation_cost=boiler_installation_cost,
)
