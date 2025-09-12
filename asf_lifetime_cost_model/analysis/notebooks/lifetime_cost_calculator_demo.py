# %%
from asf_lifetime_cost_model.pipeline.lifetime_cost_calculator import LifetimeCostCalculator

# %%
calculator = LifetimeCostCalculator()

# %%
upfront_costs = calculator.compute_upfront_cost(
    heating_system="ashp",
    annual_cost_reduction=0.05,
    purchase_year=2025,
    life_span=10,
    decile=50,
    subsidy_model_or_input_values="flat",
    purchase_with_loan=True,
    loan_interest_rate=0.05,
)
print(upfront_costs)

# %%
maintenance_costs = calculator.compute_total_maintenance_cost(
    maintenance_frequency_per_year=1, maintenance_cost=100, life_span=10
)
print(maintenance_costs)


# %%
running_costs = calculator.compute_running_cost_time_series(
    purchase_year=2025,
    life_span=10,
    heating_system_efficiency=3,
    fuel_type="electricity",
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
    include_vat=True,
)
print(running_costs)

# %%
calculator.compute_total_lifetime_costs(
    installation_costs=upfront_costs, maintenance_costs=maintenance_costs, running_costs=running_costs
)

# %%
