"""Scenarios configuration file.

Dictionary with a list of pre-set scenarios and respective arguments used
to calculate the lifetime cost of different heating systems.
"""

from asf_lifetime_cost_model import config

scenarios = {
    "baseline_A": {
        "name": "Baseline",
        "ashp_scop": "reference",
        "ashp_subsidy": "zero from 2028",
        "ashp_annual_cost_decrease": 0.01,  # moderate, 1% annual cost decrease
        "purchasing_with_loans": True,
        "loan_interest_rate": config.get("loan_interest_rate_default"),
        "wholesale_price_projection": "reference",
        "levy_rebalancing": "reference",
    },
    "scenario_B": {
        "name": "High innovation",
        "ashp_scop": "high",
        "ashp_subsidy": "fast stepdown",
        "ashp_annual_cost_decrease": 0.05,  # optimistic, 5% annual cost decrease
        "purchasing_with_loans": True,
        "loan_interest_rate": config.get("loan_interest_rate_default"),
        "wholesale_price_projection": "reference",
        "levy_rebalancing": "",  # ?
    },
    "scenario_C": {
        "name": "Cheaper electricity",
        "ashp_scop": "reference",
        "ashp_subsidy": "fast stepdown",
        "ashp_annual_cost_decrease": 0.01,  # moderate, 1% annual cost decrease
        "purchasing_with_loans": True,
        "loan_interest_rate": config.get("loan_interest_rate_default"),
        "wholesale_price_projection": "low fossil fuel prices",
        "levy_rebalancing": "",  # ?
    },
    "scenario_D": {
        "name": "High subsidy",
        "ashp_scop": "reference",
        "ashp_subsidy": "high",
        "ashp_annual_cost_decrease": 0.01,  # moderate, 1% annual cost decrease
        "purchasing_with_loans": True,
        "loan_interest_rate": config.get("loan_interest_rate_default"),
        "wholesale_price_projection": "reference",
        "levy_rebalancing": "",  # ?
    },
}
