"""Scenarios configuration file.

Dictionary with scenarios and respective arguments used
to calculate the lifetime cost of different heating systems.
"""

scenarios = {
    "baseline_A": {
        "name": "Baseline",
        "ashp_scop": "reference",
        "ashp_subsidy": "Slow stepdown",
        "ashp_market_cost_change": "moderate",
        "purchasing_with_loans": True,
        "interest_rate": 0.05,
        "fossil_fuel_prices": "reference",
        "levy_rebalancing": "reference",
        "electricity_VAT": True,
    },
    "scenario_B": {
        "name": "Innovation",
        "ashp_scop": "reference",
        "ashp_subsidy": "Zero from 2028",
        "ashp_market_cost_change": "moderate",
        "purchasing_with_loans": True,
        "interest_rate": 0.05,
        "fossil_fuel_prices": "reference",
        "levy_rebalancing": "reference",
        "electricity_VAT": True,
    },
    "scenario_C": {
        "name": "Rebalancing + low subsidies",
        "ashp_scop": "reference",
        "ashp_subsidy": "Smallest",
        "ashp_market_cost_change": "moderate",
        "purchasing_with_loans": True,
        "interest_rate": 0.05,
        "fossil_fuel_prices": "reference",
        "levy_rebalancing": "CORE model",
        "electricity_VAT": True,
    },
    "scenario_D": {
        "name": "High gas prices + high subsidy",
        "ashp_scop": "reference",
        "ashp_subsidy": "Flat",
        "ashp_market_cost_change": "moderate",
        "purchasing_with_loans": True,
        "interest_rate": 0.05,
        "fossil_fuel_prices": "high",
        "levy_rebalancing": "CORE model",
        "electricity_VAT": True,
    },
}
