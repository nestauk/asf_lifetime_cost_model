# %%
import asf_lifetime_cost_model.getters.data_getters as data_getters
import asf_lifetime_cost_model.pipeline.running_costs as running_costs

# %% [markdown]
# #### Demonstrating the functionality of the helper functions that are used in the `compute_running_costs()` function

# %% [markdown]
# **Getting property annual demand**

# %%
data_getters.get_property_heat_demand()

# %%
running_costs.get_property_heat_demand(archetype="pre_1950_semi_terraced_house")

# %%
# Testing error message
running_costs.get_property_heat_demand(archetype="invalid archetype")

# %% [markdown]
# **Getting time series of DESNZ wholesale price projections to replace wholesale price component of future energy prices**

# %%
data_getters.get_desnz_wholesale_price_projections()

# %%
# Time series output here is after applying modelling modifications
running_costs.get_wholesale_price_projection_series(
    fuel_type="gas", projection_scenario="reference"
).T

# %% [markdown]
# **Getting time series of future energy prices with the wholesale price component replaced with provided DESNZ projections**

# %%
# Create gas and electricity tariff objects
gas_tariff, electricity_tariff = data_getters.get_current_energy_price_cap_tariffs()

# Create list of operating years
purchase_year = 2025
life_span = 15
years_of_operation = list(range(purchase_year, purchase_year + life_span))

# Create a dictionary of gas and electricity tariffs for each year of operation
# Note we are using the same tariff for each year in the future
gas_tariff_time_series = {year: gas_tariff for year in years_of_operation}
electricity_tariff_time_series = {
    year: electricity_tariff for year in years_of_operation
}

# %%
gas_tariff_time_series

# %%
# Inspecting what current gas unit cost is
gas_tariff_time_series[2025].calculate_variable_consumption(1)

# %%
unit_cost_time_series, standing_charge_time_series = (
    running_costs.create_energy_cost_time_series(
        tariff_time_series=gas_tariff_time_series,
        fuel_type="gas",
        wholesale_prices_series=running_costs.get_wholesale_price_projection_series(
            fuel_type="gas", projection_scenario="reference"
        ),
    )
)

# %%
unit_cost_time_series

# %% [markdown]
# Gas unit costs get cheaper from 2025 to 2039 because the DESNZ gas wholesale price projections for "reference" scenario decrease between these years.

# %%
standing_charge_time_series

# %% [markdown]
# Gas standing charge remains constant because the DESNZ gas wholesale price projections only affect unit costs.

# %% [markdown]
# #### Demonstrating the functionality of the `compute_running_costs()` function

# %% [markdown]
# **Gas boiler running costs, with no levy rebalancing**

# %%
boiler_running_costs_time_series = running_costs.compute_running_cost_time_series(
    purchase_year=2025,
    life_span=15,
    heating_system_efficiency=0.85,
    fuel_type="gas",
    archetype="pre_1950_semi_terraced_house",
    wholesale_price_projection_scenario="reference",
    include_standing_charge=True,
    levy_rebalancing=False,
    levies_to_rebalance=None,
    levy_rebalancing_weights=None,
    include_vat=True,
)

# %%
boiler_running_costs_time_series

# %%
sum(boiler_running_costs_time_series.values())

# %% [markdown]
# **Gas boiler running costs, with levy rebalancing where the Renewables Obligation levy is rebalanced from electricity units to gas units**

# %%
boiler_running_costs_time_series = running_costs.compute_running_cost_time_series(
    purchase_year=2025,
    life_span=15,
    heating_system_efficiency=0.85,
    fuel_type="gas",
    archetype="pre_1950_semi_terraced_house",
    wholesale_price_projection_scenario="reference",
    include_standing_charge=True,
    levy_rebalancing=True,
    levies_to_rebalance=["ro"],
    levy_rebalancing_weights={
        "electricity_weight": 0,
        "gas_weight": 1,
        "tax_weight": 0,
        "fixed_electricity_weight": 0,
        "variable_electricity_weight": 0,
        "fixed_gas_weight": 0,
        "variable_gas_weight": 1,
    },
)

# %%
boiler_running_costs_time_series

# %%
sum(boiler_running_costs_time_series.values())

# %% [markdown]
# As the RO levy was rebalanced from electricity units to gas units (making gas more expensive), running a gas boiler in this scenario leads to higher running costs.

# %% [markdown]
# **Air source heat pump running costs, with no levy rebalancing**

# %%
ashp_running_costs_time_series = running_costs.compute_running_cost_time_series(
    purchase_year=2025,
    life_span=15,
    heating_system_efficiency=3.0,
    fuel_type="electricity",
    archetype="pre_1950_semi_terraced_house",
    wholesale_price_projection_scenario="reference",
    include_standing_charge=False,
    levy_rebalancing=False,
)

# %%
ashp_running_costs_time_series

# %%
sum(ashp_running_costs_time_series.values())

# %% [markdown]
# **Air source heat pump running costs, with levy rebalancing where the Renewables Obligation levy is rebalanced from electricity units to gas units**

# %%
ashp_running_costs_time_series = running_costs.compute_running_cost_time_series(
    purchase_year=2025,
    life_span=15,
    heating_system_efficiency=3.0,
    fuel_type="electricity",
    archetype="pre_1950_semi_terraced_house",
    wholesale_price_projection_scenario="reference",
    include_standing_charge=False,
    levy_rebalancing=True,
    levies_to_rebalance=["ro"],
    levy_rebalancing_weights={
        "electricity_weight": 0,
        "gas_weight": 1,
        "tax_weight": 0,
        "fixed_electricity_weight": 0,
        "variable_electricity_weight": 0,
        "fixed_gas_weight": 0,
        "variable_gas_weight": 1,
    },
)

# %%
ashp_running_costs_time_series

# %%
sum(ashp_running_costs_time_series.values())

# %% [markdown]
# As the RO levy was rebalanced from electricity units to gas units (making electricity cheaper), running an air source heat pump in this scenario leads to lower running costs.
