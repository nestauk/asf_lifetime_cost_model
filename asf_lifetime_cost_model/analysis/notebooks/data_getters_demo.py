# %% [markdown]
# ### Demonstrating how the data getters work

# %%
import pandas as pd

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
data_getters.get_desnz_wholesale_price_projections(
    projection_scenario_names=["Reference", "FFP_Low", "FFP_High"]
)

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
# If we want to extract the unit cost of gas:

# %%
current_gas_tariff.calculate_variable_consumption(1)  # in £/MWh

# %% [markdown]
# If we want to extract the gas standing charge:

# %%
current_gas_tariff.calculate_nil_consumption()  # in £/customer

# %% [markdown]
# If we want to extract a household's total gas bill (assuming we know their gas consumption) and including VAT:

# %%
current_gas_tariff.calculate_total_consumption(consumption=2.7, vat=True)

# %% [markdown]
# **Levies**
# - Uses data getters from asf_levies_model
# - Uses Levy class from asf_levies_model
# - The total cost of all levies is the "policy costs" component (pc and pc_nil) of a Tariff

# %% [markdown]
# Scenarios that are recognised by the `get_rebalanced_levies()` function include:
# - Remove all
# - Rebalance RO and FiT to gas
# - Remove from electricity
# - Rebalance electricity unit cost levies to gas
# - Rebalance all to gas
#
# This is not the most generalisable and sustainable approach as each time we want to integrate a new levy rebalancing scenario, it needs to be defined in this function. But we can revisit this later.

# %%
rebalanced_levies = data_getters.get_rebalanced_levies("rebalance RO and FiT to gas")

# %% [markdown]
# To demonstrate what has happened, consider just the Renewables Obligation (RO) levy. It was originally levied on electricity units (£/MWh of electricity), but this rebalancing scenario changes it so that it levied on gas units (£/MWh of gas).

# %%
current_levies = data_getters.get_levies(price_cap_period="LATEST")

# %%
current_levies["ro"].electricity_variable_rate, rebalanced_levies[
    "ro"
].electricity_variable_rate

# %%
current_levies["ro"].gas_variable_rate, rebalanced_levies["ro"].gas_variable_rate

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
current_gas_tariff.calculate_total_consumption(consumption=2.7, vat=True)

# %%
rebalanced_gas_tariff.calculate_total_consumption(consumption=2.7, vat=True)

# %% [markdown]
# The gas bill after rebalancing is higher because we moved some policy costs (RO and FiT) from electricity to gas.
