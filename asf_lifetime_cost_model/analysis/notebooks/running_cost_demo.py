# %% [markdown]
# Demonstrating the functionality of the `compute_running_costs()` function.

# %%
import asf_lifetime_cost_model.pipeline.running_costs as running_costs

# %%
boiler_running_costs_time_series = running_costs.compute_running_costs(
    purchase_year=2025,
    life_span=15,
    heating_system_efficiency=0.85,
    fuel_type="gas",
    archetype_number=1,
    wholesale_price_projection_scenario="reference",
    include_standing_charge=True,
    levy_rebalancing=False,
    levies_to_rebalance=None,
    levy_rebalancing_weights=None,
)

# %%
sum(boiler_running_costs_time_series.values())

# %%
boiler_running_costs_time_series = running_costs.compute_running_costs(
    purchase_year=2025,
    life_span=15,
    heating_system_efficiency=0.85,
    fuel_type="gas",
    archetype_number=1,
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
sum(boiler_running_costs_time_series.values())

# %%
ashp_running_costs_time_series = running_costs.compute_running_costs(
    purchase_year=2025,
    life_span=15,
    heating_system_efficiency=3.0,
    fuel_type="electricity",
    archetype_number=1,
    wholesale_price_projection_scenario="reference",
    include_standing_charge=False,
    levy_rebalancing=False,
)

# %%
sum(ashp_running_costs_time_series.values())

# %%
ashp_running_costs_time_series = running_costs.compute_running_costs(
    purchase_year=2025,
    life_span=15,
    heating_system_efficiency=3.0,
    fuel_type="electricity",
    archetype_number=1,
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
sum(ashp_running_costs_time_series.values())
