"""Computes lifetime cost differences between ASHP and boiler for different pre-set scenarios and saves results to S3.

These are then read in the front-end to display the scenario analysis.
"""

# Local imports
from asf_lifetime_cost_model import config
from asf_lifetime_cost_model.analysis.scenarios import scenarios
from asf_lifetime_cost_model.pipeline.lifetime_cost_calculator import (
    LifetimeCostCalculator,
)

# Package imports
import pandas as pd


for cost_decile in range(10, 20, 10):
    cost_calculator = LifetimeCostCalculator()

    archetype_name_mapping = {
        "pre_1950_flat": "Pre-1950 flat",
        "post_1950_flat": "Post-1950 flat",
        "pre_1950_semi_terraced_house": "Pre-1950 semi/terraced house",
        "post_1950_semi_terraced_house": "Post-1950 semi/terraced house",
        "pre_1950_bungalow": "Pre-1950 bungalow",
        "post_1950_bungalow": "Post-1950 bungalow",
        "pre_1950_detached_house": "Pre-1950 detached house",
        "post_1950_detached_house": "Post-1950 detached house",
    }

    # these numbers need to be QAed
    number_of_properties = {
        "Post-1950 semi/terraced house": 6841365,
        "Pre-1950 semi/terraced house": 5602441,
        "Post-1950 flat": 4076569,
        "Post-1950 detached house": 3103702,
        "Post-1950 bungalow": 1564001,
        "Pre-1950 flat": 1415792,
        "Pre-1950 detached house": 1059425,
        "Pre-1950 bungalow": 205582,
    }

    mapped_archetype_options = [archetype_name_mapping[x] for x in cost_calculator.property_archetypes]

    results = pd.DataFrame()

    installation_years = range(2024, 2035)
    for installation_year in installation_years:
        for scenario in scenarios.keys():
            if scenario != "Cheaper electricity":
                scenario_info = scenarios[scenario]
                ashp_life_span = config.get("life_span_default")["ashp"]
                boiler_life_span = config.get("life_span_default")["boiler"]
                ashp_maintenance_cost = config.get("maintenance_costs_default")["ashp"]
                boiler_maintenance_cost = config.get("maintenance_costs_default")["boiler"]
                ashp_maintenance_frequency = 1.0
                boiler_maintenance_frequency = 1.0
                ashp_efficiency = (
                    3.0
                    if scenario_info["ashp_scop"] == "reference"
                    else 3.5
                    if scenario_info["ashp_scop"] == "high"
                    else 2.5
                )
                boiler_efficiency = config.get("boiler_efficiency_default")
                ashp_purchased_with_loan = "Yes" if scenario_info["purchasing_with_loans"] else "No"

                if ashp_purchased_with_loan == "Yes":
                    ashp_loan_interes_rate = scenario_info["loan_interest_rate"]
                else:
                    ashp_loan_interes_rate = 0

                ashp_subsidy_model = scenario_info["ashp_subsidy"]
                wholesale_price_projection = scenario_info["wholesale_price_projection"]
                levy_rebalancing = scenario_info["levy_rebalancing"]

                # Processing inputs before computations
                if ashp_purchased_with_loan == "Yes":
                    ashp_purchased_with_loan = True
                    ashp_loan_interes_rate = config.get("loan_interest_rate_options")[ashp_loan_interes_rate]
                else:
                    ashp_purchased_with_loan = False
                    ashp_loan_interes_rate = 0.0

                if levy_rebalancing == "no rebalancing (current price cap)":
                    levy_rebalancing = False
                    levies_to_rebalance = None
                    levies_rebalancing_weights = None
                elif levy_rebalancing == "remove all electricity levies to taxation":
                    levy_rebalancing = True
                    levies_to_rebalance = ["ro", "fit", "eco", "whd", "aahedc", "ncc"]
                    levies_rebalancing_weights = {
                        "electricity_weight": 0,
                        "gas_weight": 1,
                        "tax_weight": 0,
                        "fixed_electricity_weight": 0,
                        "variable_electricity_weight": 0,
                        "fixed_gas_weight": 0,
                        "variable_gas_weight": 1,
                    }
                elif levy_rebalancing == "rebalance RO and FiT from electricity to gas":
                    levy_rebalancing = True
                    levies_to_rebalance = ["ro", "fit"]
                    levies_rebalancing_weights = {
                        "electricity_weight": 0,
                        "gas_weight": 1,
                        "tax_weight": 0,
                        "fixed_electricity_weight": 0,
                        "variable_electricity_weight": 0,
                        "fixed_gas_weight": 0,
                        "variable_gas_weight": 1,
                    }
                else:
                    raise ValueError("Levy rebalancing option not recognised")

                ashp_upfront_costs = cost_calculator.compute_upfront_cost(
                    heating_system="ashp",
                    annual_cost_reduction=0.05,
                    purchase_year=installation_year,
                    life_span=ashp_life_span,
                    decile=cost_decile,
                    subsidy_model_or_input_values=ashp_subsidy_model,
                    purchase_with_loan=ashp_purchased_with_loan,
                    loan_interest_rate=ashp_loan_interes_rate,
                )

                ashp_maintenance_costs = cost_calculator.compute_total_maintenance_cost(
                    maintenance_frequency_per_year=ashp_maintenance_frequency,
                    maintenance_cost=ashp_maintenance_cost,
                    life_span=ashp_life_span,
                )

                ashp_running_costs = cost_calculator.compute_running_cost_time_series(
                    purchase_year=installation_year,
                    life_span=ashp_life_span,
                    heating_system_efficiency=ashp_efficiency,
                    fuel_type="electricity",
                    wholesale_price_projection_scenario=wholesale_price_projection,
                    include_standing_charge=False,
                    levy_rebalancing=levy_rebalancing,
                    levies_to_rebalance=levies_to_rebalance,
                    levy_rebalancing_weights=levies_rebalancing_weights,
                    include_vat=True,
                )

                ashp_lifetime_costs = cost_calculator.compute_total_lifetime_costs(
                    installation_costs=ashp_upfront_costs,
                    maintenance_costs=ashp_maintenance_costs,
                    running_costs=ashp_running_costs,
                )

                boiler_upfront_costs = cost_calculator.compute_upfront_cost(
                    heating_system="boiler",
                    annual_cost_reduction=0,
                    purchase_year=installation_year,
                    life_span=ashp_life_span,
                )
                boiler_maintenance_costs = cost_calculator.compute_total_maintenance_cost(
                    maintenance_frequency_per_year=boiler_maintenance_frequency,
                    maintenance_cost=boiler_maintenance_cost,
                    life_span=boiler_life_span,
                )
                boiler_running_costs = cost_calculator.compute_running_cost_time_series(
                    purchase_year=installation_year,
                    life_span=boiler_life_span,
                    heating_system_efficiency=boiler_efficiency,
                    fuel_type="gas",
                    wholesale_price_projection_scenario=wholesale_price_projection,
                    include_standing_charge=True,
                    levy_rebalancing=levy_rebalancing,
                    levies_to_rebalance=levies_to_rebalance,
                    levy_rebalancing_weights=levies_rebalancing_weights,
                    include_vat=True,
                )
                boiler_lifetime_costs = cost_calculator.compute_total_lifetime_costs(
                    installation_costs=boiler_upfront_costs,
                    maintenance_costs=boiler_maintenance_costs,
                    running_costs=boiler_running_costs,
                )

                ashp_lifetime_costs.reset_index(inplace=True)
                boiler_lifetime_costs.reset_index(inplace=True)

                lifetime_costs = ashp_lifetime_costs[["archetype_label", "total_lifetime_costs"]].merge(
                    boiler_lifetime_costs[["archetype_label", "total_lifetime_costs"]],
                    on="archetype_label",
                    how="left",
                    suffixes=("_ashp", "_boiler"),
                )
                lifetime_costs["cost_difference_ashp_minus_boiler"] = (
                    lifetime_costs["total_lifetime_costs_ashp"] - lifetime_costs["total_lifetime_costs_boiler"]
                )

                lifetime_costs["archetype_label"] = lifetime_costs["archetype_label"].map(archetype_name_mapping)

                # add property counts
                lifetime_costs["number_of_properties"] = lifetime_costs["archetype_label"].map(number_of_properties)

                # compute weighted average archetype
                weighted_avg = (
                    lifetime_costs["cost_difference_ashp_minus_boiler"] * lifetime_costs["number_of_properties"]
                ).sum() / lifetime_costs["number_of_properties"].sum()

                results.loc[installation_year, scenario] = weighted_avg
                print(results)
    results.to_csv("s3://asf-lifetime-cost-model/outputs/cost_dif_by_year_decile_" + str(cost_decile) + ".csv")
