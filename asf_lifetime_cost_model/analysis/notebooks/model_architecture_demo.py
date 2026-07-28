# -*- coding: utf-8 -*-
# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     custom_cell_magics: kql
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.11.2
#   kernelspec:
#     display_name: asf_lifetime_cost_model (3.13.2)
#     language: python
#     name: python3
# ---

# %%
import pandas as pd

import asf_lifetime_cost_model.getters.data_getters as data_getters
from asf_lifetime_cost_model.models.energy_price_trajectory import EnergyPriceTrajectory
from asf_lifetime_cost_model.models.heating_system import HeatingSystem
from asf_lifetime_cost_model.models.installation_cost_trajectory import InstallationCostTrajectory
from asf_lifetime_cost_model.models.subsidy_trajectory import SubsidyTrajectory

from asf_lifetime_cost_model import config

# %% [markdown]
# ## EnergyPriceTrajectory

# %%
electricity_prices = EnergyPriceTrajectory(
    fuel="electricity",
    starting_price=data_getters.get_latest_price_cap_rate("electricity"),
    price_basis="real",
    base_year=2026,
)
electricity_prices.set_trajectory(-0.02, from_year=2027)  # -2%/year, already in real terms
# electricity_prices.set_trajectory({2030: 10.0})  # explicit override example

electricity_prices

# %%
gas_prices = EnergyPriceTrajectory(
    fuel="gas", starting_price=data_getters.get_latest_price_cap_rate("gas"), price_basis="real", base_year=2026
)
gas_prices

# %% [markdown]
# ## InstallationCostTrajectory

# %%
boiler_installation_costs = InstallationCostTrajectory(
    "gas_boiler",
    starting_cost=3_000,
    price_basis="real",  # 3,000 is already stated in 2026 real £
    base_year=2026,
)
boiler_installation_costs
# no set_trajectory call needed
# the flat starting value across all years already represents "0% real change"

# %%
ashp_installation_costs = InstallationCostTrajectory(
    system_type="air_to_water_heat_pump", starting_cost=13_100, price_basis="real", base_year=2026
)
ashp_installation_costs.set_trajectory(-0.025)
ashp_installation_costs

# %%
ashp_installation_costs.cost

# %% [markdown]
# ## SubsidyTrajectory

# %%
ashp_subsidies = SubsidyTrajectory(system_type="air_to_water_heat_pump", starting_subsidy=7_500, price_basis="nominal")

# %%
# example setting trajectory to one of subsidy pathway options
subsidy_options = data_getters.get_ashp_subsidy_options_data()
fast_stepdown_row = subsidy_options.set_index("model").loc["fast stepdown"]
fast_stepdown_values = {
    int(year): value for year, value in fast_stepdown_row.items() if int(year) in ashp_subsidies.subsidy.index
}
ashp_subsidies.set_trajectory(fast_stepdown_values)
ashp_subsidies.to_real(base_year=2026, inflation_rate=config["default_inflation_rate"])
ashp_subsidies

# %%
ashp_subsidies.subsidy

# %% [markdown]
# ## HeatingSystem

# %% [markdown]
# **Heat pump - no financing**

# %%
# Heat pump
heat_pump = HeatingSystem(
    system_type="air_to_water_heat_pump",
    installation_year=2026,
    lifespan=15,
    efficiency=3.0,
    installation_cost_trajectory=ashp_installation_costs,
    subsidy_trajectory=ashp_subsidies,
    maintenance_cost_per_visit=80.0,
    maintenance_annual_frequency=1.0,  # annual maintenance
)
heat_pump

# %%
# Configure heat demand
gas_tdcv = 9_500  # kWh
heat_demand_uplift_with_heat_pump = 0.08
heat_demand_with_heat_pump = (9_500 * 0.85) * (1 + heat_demand_uplift_with_heat_pump)


# %%
# discounted lifetime running cost for a chosen year
heat_pump.calculate_discounted_running_cost(
    year=2026, heat_demand=heat_demand_with_heat_pump, energy_price_trajectory=electricity_prices
)

# %%
# error is raised if you try to get a running cost for a year that is outside its lifetime
heat_pump.calculate_discounted_running_cost(
    year=2045, heat_demand=heat_demand_with_heat_pump, energy_price_trajectory=electricity_prices
)

# %%
# lifetime running cost
heat_pump.calculate_lifetime_running_cost(heat_demand_with_heat_pump, electricity_prices)

# %%
# discounted lifetime running cost
heat_pump.calculate_discounted_lifetime_running_cost(heat_demand_with_heat_pump, electricity_prices)

# %%
# capex (no financing)
heat_pump.calculate_lifetime_capital_cost()

# %%
# raises error if you use a method related to loan interest/repayments
heat_pump.calculate_annual_loan_repayment()

# %%
# maintenance cost (undiscounted, average annual)
heat_pump.calculate_annual_maintenance_cost()

# %%
# discounted maintenance cost for a given year
heat_pump.calculate_discounted_maintenance_cost(year=2028)

# %%
# discounted lifetime maintenance cost
heat_pump.calculate_discounted_lifetime_maintenance_cost()

# %%
# lifetime cost
heat_pump.calculate_lifetime_cost(heat_demand_with_heat_pump, electricity_prices)

# %%
# annualised lifetime cost
heat_pump.calculate_annualised_lifetime_cost(heat_demand_with_heat_pump, electricity_prices)

# %%
# discounted lifetime cost
heat_pump.calculate_discounted_lifetime_cost(heat_demand_with_heat_pump, electricity_prices)

# %%
# discounted annualised lifetime cost
heat_pump.calculate_annualised_discounted_lifetime_cost(heat_demand_with_heat_pump, electricity_prices)

# %% [markdown]
# **Heat pump with financing**

# %%
# Heat pump financed
heat_pump_financed = HeatingSystem(
    system_type="air_to_water_heat_pump",
    installation_year=2026,
    lifespan=15,
    efficiency=3.0,
    installation_cost_trajectory=ashp_installation_costs,
    subsidy_trajectory=ashp_subsidies,
    maintenance_cost_per_visit=80.0,
    maintenance_annual_frequency=1.0,  # annual maintenance
    interest_rate=0.05,
    loan_term=15,
)
heat_pump_financed

# %%
# Configure heat demand
gas_tdcv = 9_500  # kWh
heat_demand_uplift_with_heat_pump = 0.08
heat_demand_with_heat_pump = (9_500 * 0.85) * (1 + heat_demand_uplift_with_heat_pump)

# %%
# annual loan repayment
heat_pump_financed.calculate_annual_loan_repayment()

# %%
# get discounted loan repayment for a given year
heat_pump_financed.calculate_discounted_loan_repayment(year=2026)

# %%
# get discounted loan repayment for a given year
heat_pump_financed.calculate_discounted_loan_repayment(year=2030)

# %%
# lifetime capital cost
heat_pump_financed.calculate_lifetime_capital_cost()

# %%
# interest portion of capex only
heat_pump_financed.calculate_lifetime_loan_interest()

# %%
assert (
    heat_pump.upfront_cost
    == heat_pump_financed.calculate_lifetime_capital_cost() - heat_pump_financed.calculate_lifetime_loan_interest()
)

# %%
# lifetime capital cost
heat_pump_financed.calculate_discounted_lifetime_capital_cost()

# %%
# interest portion of capex only
heat_pump_financed.calculate_discounted_lifetime_loan_interest()

# %%
assert (
    heat_pump.upfront_cost
    == heat_pump_financed.calculate_discounted_lifetime_capital_cost()
    - heat_pump_financed.calculate_discounted_lifetime_loan_interest()
)

# %%
# lifetime cost
heat_pump_financed.calculate_lifetime_cost(heat_demand_with_heat_pump, electricity_prices)

# %%
# annualised lifetime cost
heat_pump_financed.calculate_annualised_lifetime_cost(heat_demand_with_heat_pump, electricity_prices)

# %%
# discounted lifetime cost
heat_pump_financed.calculate_discounted_lifetime_cost(heat_demand_with_heat_pump, electricity_prices)

# %%
# discounted annualised lifetime cost
heat_pump_financed.calculate_annualised_discounted_lifetime_cost(heat_demand_with_heat_pump, electricity_prices)

# %% [markdown]
# **Gas boiler**

# %%
# Boiler
gas_boiler_subsidies = SubsidyTrajectory(
    system_type="gas_boiler", starting_subsidy=0.0, price_basis="real", base_year=2026
)

gas_boiler = HeatingSystem(
    system_type="gas_boiler",
    installation_year=2026,
    lifespan=15,
    efficiency=0.85,
    installation_cost_trajectory=boiler_installation_costs,
    subsidy_trajectory=gas_boiler_subsidies,
    maintenance_cost_per_visit=80.0,
    maintenance_annual_frequency=1.0,
)

# %%
gas_tdcv = 9_500  # kWh
heat_demand_with_boiler = 9_500 * 0.85

# %%
gas_boiler.calculate_discounted_lifetime_capital_cost()

# %%
gas_boiler.calculate_discounted_lifetime_running_cost(heat_demand_with_boiler, gas_prices)

# %%
gas_boiler.calculate_discounted_lifetime_maintenance_cost()

# %%
gas_boiler.calculate_discounted_lifetime_cost(heat_demand_with_boiler, gas_prices)

# %%
gas_boiler.calculate_annualised_discounted_lifetime_cost(heat_demand_with_boiler, gas_prices)

# %% [markdown]
# **Gas boiler with gas standing charge attributed**

# %%
gas_standing_charge = data_getters.get_latest_price_cap_standing_charge(fuel="gas")
gas_standing_charge  # p/day

# %%
gas_boiler.calculate_discounted_lifetime_running_cost(heat_demand_with_boiler, gas_prices, gas_standing_charge)

# %%
gas_boiler.calculate_discounted_lifetime_cost(heat_demand_with_boiler, gas_prices, gas_standing_charge)

# %%
gas_boiler.calculate_annualised_discounted_lifetime_cost(heat_demand_with_boiler, gas_prices, gas_standing_charge)

# %% [markdown]
# **Comparison**

# %%
comparison_data = {
    "Heat pump": {
        "Installation year": heat_pump.installation_year,
        "Lifespan": heat_pump.lifespan,
        "Efficiency": heat_pump.efficiency,
        "Heat demand (kWh/year)": heat_demand_with_heat_pump,
        "Interest rate": None,
        "Loan term": None,
        "Discounted capital cost": heat_pump.calculate_discounted_lifetime_capital_cost(),
        "...of which loan interest": (
            heat_pump.calculate_discounted_lifetime_loan_interest() if heat_pump.is_financed else 0.0
        ),
        "Discounted maintenance cost": heat_pump.calculate_discounted_lifetime_maintenance_cost(),
        "Discounted running cost": heat_pump.calculate_discounted_lifetime_running_cost(
            heat_demand_with_heat_pump, electricity_prices
        ),
        "Total discounted lifetime cost": heat_pump.calculate_discounted_lifetime_cost(
            heat_demand_with_heat_pump, electricity_prices
        ),
        "Annualised discounted lifetime cost (EAC)": heat_pump.calculate_annualised_discounted_lifetime_cost(
            heat_demand_with_heat_pump, electricity_prices
        ),
    },
    "Heat pump (financed)": {
        "Installation year": heat_pump_financed.installation_year,
        "Lifespan": heat_pump_financed.lifespan,
        "Efficiency": heat_pump_financed.efficiency,
        "Heat demand (kWh/year)": heat_demand_with_heat_pump,
        "Interest rate": heat_pump_financed.interest_rate,
        "Loan term": heat_pump_financed.loan_term,
        "Discounted capital cost": heat_pump_financed.calculate_discounted_lifetime_capital_cost(),
        "...of which loan interest": (
            heat_pump_financed.calculate_discounted_lifetime_loan_interest() if heat_pump_financed.is_financed else 0.0
        ),
        "Discounted maintenance cost": heat_pump_financed.calculate_discounted_lifetime_maintenance_cost(),
        "Discounted running cost": heat_pump_financed.calculate_discounted_lifetime_running_cost(
            heat_demand_with_heat_pump, electricity_prices
        ),
        "Total discounted lifetime cost": heat_pump_financed.calculate_discounted_lifetime_cost(
            heat_demand_with_heat_pump, electricity_prices
        ),
        "Annualised discounted lifetime cost (EAC)": heat_pump_financed.calculate_annualised_discounted_lifetime_cost(
            heat_demand_with_heat_pump, electricity_prices
        ),
    },
    "Gas boiler": {
        "Installation year": gas_boiler.installation_year,
        "Lifespan": gas_boiler.lifespan,
        "Efficiency": gas_boiler.efficiency,
        "Heat demand (kWh/year)": heat_demand_with_boiler,
        "Interest rate": None,
        "Loan term": None,
        "Discounted capital cost": gas_boiler.calculate_discounted_lifetime_capital_cost(),
        "...of which loan interest": (
            gas_boiler.calculate_discounted_lifetime_loan_interest() if gas_boiler.is_financed else 0.0
        ),
        "Discounted maintenance cost": gas_boiler.calculate_discounted_lifetime_maintenance_cost(),
        "Discounted running cost": gas_boiler.calculate_discounted_lifetime_running_cost(
            heat_demand_with_boiler, gas_prices
        ),
        "Total discounted lifetime cost": gas_boiler.calculate_discounted_lifetime_cost(
            heat_demand_with_boiler, gas_prices
        ),
        "Annualised discounted lifetime cost (EAC)": gas_boiler.calculate_annualised_discounted_lifetime_cost(
            heat_demand_with_boiler, gas_prices
        ),
    },
    "Gas boiler (incl. gas standing charge)": {
        "Installation year": gas_boiler.installation_year,
        "Lifespan": gas_boiler.lifespan,
        "Efficiency": gas_boiler.efficiency,
        "Heat demand (kWh/year)": heat_demand_with_boiler,
        "Interest rate": None,
        "Loan term": None,
        "Discounted capital cost": gas_boiler.calculate_discounted_lifetime_capital_cost(),
        "...of which loan interest": (
            gas_boiler.calculate_discounted_lifetime_loan_interest() if gas_boiler.is_financed else 0.0
        ),
        "Discounted maintenance cost": gas_boiler.calculate_discounted_lifetime_maintenance_cost(),
        "Discounted running cost": gas_boiler.calculate_discounted_lifetime_running_cost(
            heat_demand_with_boiler, gas_prices, gas_standing_charge
        ),
        "Total discounted lifetime cost": gas_boiler.calculate_discounted_lifetime_cost(
            heat_demand_with_boiler, gas_prices, gas_standing_charge
        ),
        "Annualised discounted lifetime cost (EAC)": gas_boiler.calculate_annualised_discounted_lifetime_cost(
            heat_demand_with_boiler, gas_prices, gas_standing_charge
        ),
    },
}

comparison_df = pd.DataFrame(comparison_data)

integer_rows = ["Installation year", "Lifespan", "Loan term"]
percentage_rows = ["Interest rate"]
plain_number_rows = ["Efficiency", "Heat demand (kWh/year)"]
currency_rows = [row for row in comparison_df.index if row not in integer_rows + percentage_rows + plain_number_rows]

formatted_df = comparison_df.copy().astype(object)

for row in integer_rows:
    formatted_df.loc[row] = comparison_df.loc[row].map(lambda value: "n/a" if pd.isna(value) else f"{int(value)}")

for row in percentage_rows:
    formatted_df.loc[row] = comparison_df.loc[row].map(lambda value: "n/a" if pd.isna(value) else f"{value:.1%}")

for row in plain_number_rows:
    formatted_df.loc[row] = comparison_df.loc[row].map(lambda value: "n/a" if pd.isna(value) else f"{value:,.2f}")

formatted_df.loc[currency_rows] = comparison_df.loc[currency_rows].map(lambda value: f"£{value:,.2f}")

formatted_df
