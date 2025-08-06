"""Scenarios configuration file.

Dictionary with a list of pre-set scenarios and respective arguments used
to calculate the lifetime cost of different heating systems.
"""

from asf_lifetime_cost_model import config

scenarios = {
    "baseline_A": {
        "name": "Baseline",
        "ashp_scop": "reference",
        "ashp_subsidy": "Slow stepdown",
        "ashp_market_cost_change": "moderate",
        "purchasing_with_loans": True,
        "loan_interest_rate": config.get("loan_interest_rate_default"),
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
        "loan_interest_rate": config.get("loan_interest_rate_default"),
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
        "loan_interest_rate": config.get("loan_interest_rate_default"),
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
        "interest_rate": config.get("loan_interest_rate_default"),
        "fossil_fuel_prices": "high",
        "levy_rebalancing": "CORE model",
        "electricity_VAT": True,
    },
}
