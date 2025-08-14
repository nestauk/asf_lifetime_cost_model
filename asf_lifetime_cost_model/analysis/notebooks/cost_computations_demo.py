# %%
from asf_lifetime_cost_model.pipeline import cost_computations

# %% [markdown]
# The cost of installing an air source heat pump, subtracting the subsidy from the upfront cost:

# %%
cost_computations.compute_upfront_cost(
    heating_system="ashp",
    archetype="pre_1950_semi_terraced_house_5_rooms",
    annual_cost_reduction=0.01,
    installation_year=2026,
    subtract_subsidy=True,
    decile=50,
    subsidy_model="flat",
)

# %% [markdown]
# The cost of installing an air source heat pump, WITHOUT subtracting the subsidy from the upfront cost:

# %%
cost_computations.compute_upfront_cost(
    heating_system="ashp",
    archetype="pre_1950_semi_terraced_house_5_rooms",
    annual_cost_reduction=0.01,
    installation_year=2026,
    subtract_subsidy=False,
    decile=50,
    subsidy_model="flat",
)

# %%


# %% [markdown]
# The cost of installing a gas boiler:

# %%
cost_computations.compute_upfront_cost(
    heating_system="boiler",
    archetype="bungalows pre-1950",
    annual_cost_reduction=0.01,
    installation_year=2026,
    subtract_subsidy=False,
)

# %% [markdown]
# Total maintenance costs:

# %%
cost_computations.compute_total_maintenance_cost(annual_maintenance_costs=80, life_span=15)

# %% [markdown]
# Total lifetime cost for an air source heat pump:

# %%
cost_computations.compute_total_lifetime_costs(
    heating_system="ashp",
    archetype="pre_1950_semi_terraced_house_5_rooms",
    decile=50,
    annual_cost_reduction=0.01,
    installation_year=2026,
    subtract_subsidy=True,
    subsidy_model="flat",
    annual_maintenance_costs=80,
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
    installation_year=2026,
    subtract_subsidy=True,
    subsidy_model="flat",
    annual_maintenance_costs=80,
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
    installation_year=2026,
    subtract_subsidy=True,
    subsidy_model="flat",
    annual_maintenance_costs=80,
    life_span=15,
)

# %% [markdown]
# Dictionary with breakdown of costs given a total cost, installation year and life span:

# %%
cost_computations.create_cost_breakdown_per_year_in_lifetime(cost_value=4110.897, life_span=15, installation_year=2026)

# %%
