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

# %% [markdown]
# ### Demonstrating how the data getters work

# %%
import asf_lifetime_cost_model.getters.data_getters as data_getters

# %% [markdown]
# **ASHP installation costs**
# - Read from .csv in s3
# - Units are £ (2023 prices)

# %%
data_getters.get_ashp_installation_costs()

# %% [markdown]
# **Property heat demand**
# - Read from .csv in s3
# - Units are kWh/year

# %%
data_getters.get_property_heat_demand()

# %% [markdown]
# **DESNZ wholesale price of natural gas and electricity projections**
# - Read from DESNZ website

# %%
data_getters.get_desnz_wholesale_price_projections()

# %% [markdown]
# **Energy price cap data**
# - Uses data getters from asf_levies_model
# - Uses Tariff class from asf_levies_model

# %%
# Instantiate Tariff objects for current price cap
current_gas_tariff, current_electricity_tariff = (
    data_getters.get_current_energy_price_cap_tariffs()
)

# %% [markdown]
# Inspecting all attributes of the Tariff object:

# %%
current_gas_tariff.__dict__

# %% [markdown]
# If we want to extract the unit cost of gas (consumption of 1 unit):

# %%
current_gas_tariff.calculate_variable_consumption(consumption = 1)  # in £/MWh

# %% [markdown]
# If we want to extract the gas standing charge:

# %%
current_gas_tariff.calculate_nil_consumption()  # in £/customer

# %% [markdown]
# If we want to extract a household's total gas bill (assuming we know their gas consumption) and including VAT:

# %%
current_gas_tariff.calculate_total_consumption(consumption=2.7, vat=True) # consumption as annual consumption in MWh

# %% [markdown]
# **Levies**
# - Uses data getters from asf_levies_model
# - Uses Levy class from asf_levies_model
# - The total cost of all levies is the "policy costs" component (pc and pc_nil) of a Tariff

# %% [markdown]
# To create a set of Levy objects (held as a LevyCollection object) representing the levies from the most recent price cap, we use the following data getter:

# %%
current_levies = data_getters.get_levies(price_cap_period="LATEST")

# %%
current_levies

# %% [markdown]
# Let's say we want to apply a levy rebalancing scenario where we want all levies to be rebalanced to gas units.

# %%
# create list of short names of levies we want to rebalance
levies_to_rebalance = [
    levy.short_name for levy in current_levies
]  # we want all of them

# %%
# provide getter function with list of levies, rebalancing weights and date of price cap period we're interested in
rebalanced_levies = data_getters.get_rebalanced_levies(
    levies_to_rebalance=levies_to_rebalance,
    electricity_weight=0,
    gas_weight=1,  # rebalance all to gas
    tax_weight=0,
    variable_electricity_weight=0,
    fixed_electricity_weight=0,
    variable_gas_weight=1,  # all on gas units
    fixed_gas_weight=0,
)

# %% [markdown]
# To demonstrate what has happened, consider just the Renewables Obligation (RO) levy. It was originally levied on electricity units (£/MWh of electricity), but this rebalancing scenario changes it so that it levied on gas units (£/MWh of gas).

# %%
current_levies["ro"].electricity_variable_rate, rebalanced_levies[
    "ro"
].electricity_variable_rate

# %%
current_levies["ro"].gas_variable_rate, rebalanced_levies["ro"].gas_variable_rate

# %% [markdown]
# Let's test another rebalancing scenario where we only want a subset of levies to be rebalanced.

# %%
levies_to_rebalance = ["fit"]  # only want to rebalance fit

# %%
rebalanced_fit_only = data_getters.get_rebalanced_levies(
    levies_to_rebalance=levies_to_rebalance,
    electricity_weight=0,
    gas_weight=1,  # rebalance all to gas
    tax_weight=0,
    variable_electricity_weight=0,
    fixed_electricity_weight=0,
    variable_gas_weight=1,  # all on gas units
    fixed_gas_weight=0,
)

# %% [markdown]
# Checking that the levy rates for FiT were successfully rebalanced

# %%
current_levies["fit"].electricity_variable_rate, rebalanced_fit_only[
    "fit"
].electricity_variable_rate

# %%
current_levies["fit"].gas_variable_rate, rebalanced_fit_only["fit"].gas_variable_rate

# %% [markdown]
# Check that a levy we didn't want rebalanced remains unaffected

# %%
current_levies["ro"].electricity_variable_rate, rebalanced_fit_only[
    "ro"
].electricity_variable_rate

# %%
current_levies["ro"].gas_variable_rate, rebalanced_fit_only["ro"].gas_variable_rate

# %% [markdown]
# **Replacing the policy costs component of a Tariff with rebalanced levies**

# %% [markdown]
# We wrote a method that takes a LevyCollection and calculates its policy costs, then substitutes those policy costs into an existing gas and electricity tariff

# %%
rebalanced_gas_tariff = current_gas_tariff.update_policy_costs(rebalanced_levies)
rebelanced_electricity_tariff = current_electricity_tariff.update_policy_costs(
    rebalanced_levies
)

# %% [markdown]
# We can compare a household's energy bill before and after rebalancing

# %%
current_gas_tariff.calculate_total_consumption(consumption=2.7, vat=True) # consumption as annual consumption in MWh

# %%
rebalanced_gas_tariff.calculate_total_consumption(consumption=2.7, vat=True) # consumption as annual consumption in MWh

# %% [markdown]
# In the example above, the gas bill after rebalancing is higher because we moved some policy costs (RO and FiT) from electricity to gas.

# %% [markdown]
# ---

# %% [markdown]
# Additional: demonstrating how the NCC levy is not included if we choose a price cap period where it didn't exist yet

# %%
levies_to_test = data_getters.get_levies(price_cap_period="2024-01-01")

# %%
levies_to_test

# %% [markdown]
# The NCC levy is successfully excluded from this instantiatied LevyCollection.
