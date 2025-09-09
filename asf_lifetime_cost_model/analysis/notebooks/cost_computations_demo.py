# %%
from asf_lifetime_cost_model.pipeline import cost_computations

# %% [markdown]
# The cost of installing an air source heat pump, subtracting the subsidy from the upfront cost:

# %%
cost_computations.compute_upfront_cost(
    heating_system="ashp",
    archetype="pre_1950_semi_terraced_house_5_rooms",
    annual_cost_reduction=0.01,
    purchase_year=2026,
    decile=50,
    subsidy_model_or_input_values="flat",
)

# %% [markdown]
# The cost of installing an air source heat pump, WITHOUT subtracting the subsidy from the upfront cost:

# %%
cost_computations.compute_upfront_cost(
    heating_system="ashp",
    archetype="pre_1950_semi_terraced_house_5_rooms",
    annual_cost_reduction=0.01,
    purchase_year=2026,
    decile=50,
    subsidy_model_or_input_values="no subsidy",
)

# %% [markdown]
# The cost of installing an air source heat pump, subtracting an inputed subsidy from the upfront cost:

# %%
cost_computations.compute_upfront_cost(
    heating_system="ashp",
    archetype="pre_1950_semi_terraced_house_5_rooms",
    annual_cost_reduction=0.01,
    purchase_year=2026,
    decile=50,
    subsidy_model_or_input_values={2025: 9000, 2026: 9500, 2027: 9575},
)

# %% [markdown]
# Testing what happens if subsidy model is wrong:

# %%
cost_computations.compute_upfront_cost(
    heating_system="ashp",
    archetype="pre_1950_semi_terraced_house_5_rooms",
    annual_cost_reduction=0.01,
    purchase_year=2026,
    decile=50,
    subsidy_model_or_input_values="f",
)

# %% [markdown]
# The cost of installing a gas boiler:

# %%
cost_computations.compute_upfront_cost(
    heating_system="boiler", archetype="bungalows pre-1950", annual_cost_reduction=0.01, purchase_year=2026
)

# %%
cost_computations.compute_upfront_cost(
    heating_system="boiler", archetype="bungalows pre-1950", annual_cost_reduction=0.01, purchase_year=2026
)

# %% [markdown]
# Checking what happens if purchase year is above max:

# %%
cost_computations.compute_upfront_cost(
    heating_system="boiler", archetype="bungalows pre-1950", annual_cost_reduction=0.01, purchase_year=2037
)

# %% [markdown]
# Checking what happens if purchase year if wrong heating system inputed:

# %%
cost_computations.compute_upfront_cost(
    heating_system="b", archetype="bungalows pre-1950", annual_cost_reduction=0.01, purchase_year=2026
)

# %% [markdown]
# Total maintenance costs:

# %%
cost_computations.compute_total_maintenance_cost(maintenance_cost=80, maintenance_frequency_per_year=1, life_span=15)

# %% [markdown]
# Total lifetime cost for an air source heat pump:

# %%
cost_computations.compute_total_lifetime_costs(
    heating_system="ashp",
    archetype="pre_1950_semi_terraced_house_5_rooms",
    decile=50,
    annual_cost_reduction=0.01,
    purchase_year=2026,
    subsidy_model_or_input_values="flat",
    maintenance_cost=80,
    maintenance_frequency_per_year=0.5,
    life_span=15,
)

# %% [markdown]
# Total lifetime cost for an air source heat pump:

# %%
cost_computations.compute_total_lifetime_costs(
    heating_system="ashp",
    archetype="pre_1950_semi_terraced_house_5_rooms",
    decile=50,
    annual_cost_reduction=0.01,
    purchase_year=2026,
    subsidy_model_or_input_values="flat",
    maintenance_cost=120,
    maintenance_frequency_per_year=2,
    life_span=15,
)

# %% [markdown]
# Total lifetime cost for an gas boiler:

# %%
cost_computations.compute_total_lifetime_costs(
    heating_system="boiler",
    archetype="bungalows pre-1950",
    decile=50,
    annual_cost_reduction=0.01,
    purchase_year=2026,
    maintenance_cost=50,
    maintenance_frequency_per_year=0.24,
    life_span=15,
)

# %% [markdown]
# Dictionary with breakdown of costs given a total cost, installation year and life span:

# %%
cost_computations.create_annualised_cost_time_series(cost_value=4110.897, life_span=15, purchase_year=2026)

# %%
