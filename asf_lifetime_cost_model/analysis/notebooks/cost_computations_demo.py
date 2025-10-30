# %% [markdown]
# ### OUTDATED NOTEBOOK
#
# `cost_computations.py` was replaced with `lifetime_cost_calculator.py`

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
# Testing purchasing with loan:

# %%
cost_computations.compute_upfront_cost(
    heating_system="ashp",
    archetype="pre_1950_semi_terraced_house_5_rooms",
    annual_cost_reduction=0.01,
    purchase_year=2026,
    decile=50,
    subsidy_model_or_input_values="no subsidy",
    purchase_with_loan=True,
    loan_interest_rate=0.05,
    life_span=7,
)

# %% [markdown]
# The cost of installing an air source heat pump with a subsidy and purchased with a 5% loan:

# %%
cost_computations.compute_upfront_cost(
    heating_system="ashp",
    life_span=15,
    archetype="pre_1950_semi_terraced_house_5_rooms",
    annual_cost_reduction=0.01,
    purchase_year=2026,
    decile=50,
    subsidy_model_or_input_values="flat",
    purchase_with_loan=True,
    loan_interest_rate=0.05,
)

# %% [markdown]
# We can calculate how much interest added to the upfront cost by
# calculating the difference between purchasing with and without loan

# %%
upfront_cost_with_loan = cost_computations.compute_upfront_cost(
    heating_system="ashp",
    life_span=15,
    archetype="pre_1950_semi_terraced_house_5_rooms",
    annual_cost_reduction=0.01,
    purchase_year=2026,
    decile=50,
    subsidy_model_or_input_values="flat",
    purchase_with_loan=True,
    loan_interest_rate=0.05,
)

upfront_cost_without_loan = cost_computations.compute_upfront_cost(
    heating_system="ashp",
    life_span=15,
    archetype="pre_1950_semi_terraced_house_5_rooms",
    annual_cost_reduction=0.01,
    purchase_year=2026,
    decile=50,
    subsidy_model_or_input_values="flat",
    purchase_with_loan=False,
)

interest = upfront_cost_with_loan - upfront_cost_without_loan
print(interest)

# %%
# Annualised
annualised_interest = interest / 15
print(annualised_interest)

# %% [markdown]
# Testing if purchasing with loan with 0% interest rate

# %%
cost_computations.compute_upfront_cost(
    heating_system="ashp",
    life_span=15,
    archetype="pre_1950_semi_terraced_house_5_rooms",
    annual_cost_reduction=0.01,
    purchase_year=2026,
    decile=50,
    subsidy_model_or_input_values="flat",
    purchase_with_loan=True,
    loan_interest_rate=0.0,
)

# %%
cost_computations.compute_upfront_cost(
    heating_system="ashp",
    life_span=15,
    archetype="pre_1950_semi_terraced_house_5_rooms",
    annual_cost_reduction=0.01,
    purchase_year=2026,
    decile=50,
    subsidy_model_or_input_values="flat",
    purchase_with_loan=True,
)

# %% [markdown]
# The cost of installing a gas boiler:

# %%
cost_computations.compute_upfront_cost(
    heating_system="boiler",
    life_span=15,
    archetype="bungalows pre-1950",
    annual_cost_reduction=0.01,
    purchase_year=2026,
)

# %% [markdown]
# Checking what happens if purchase year is above max:

# %%
cost_computations.compute_upfront_cost(
    heating_system="boiler",
    life_span=15,
    archetype="bungalows pre-1950",
    annual_cost_reduction=0.01,
    purchase_year=2037,
)

# %% [markdown]
# Checking what happens if purchase year if wrong heating system inputed:

# %%
cost_computations.compute_upfront_cost(
    heating_system="b",
    life_span=15,
    archetype="bungalows pre-1950",
    annual_cost_reduction=0.01,
    purchase_year=2026,
)

# %% [markdown]
# Total maintenance costs:

# %%
cost_computations.compute_total_maintenance_cost(
    maintenance_cost=80, maintenance_frequency_per_year=1, life_span=15
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
# Total lifetime cost for an air source heat pump with loan:

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
    purchase_with_loan=True,
    loan_interest_rate=0.05,
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
cost_computations.create_annualised_cost_time_series(
    cost_value=4110.897, life_span=15, purchase_year=2026
)

# %%
