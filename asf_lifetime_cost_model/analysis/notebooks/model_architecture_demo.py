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
import asf_lifetime_cost_model.getters.data_getters as data_getters
from asf_lifetime_cost_model.models.energy_price_trajectory import EnergyPriceTrajectory
from asf_lifetime_cost_model.models.heating_system import HeatingSystem
from asf_lifetime_cost_model.models.household import Household
from asf_lifetime_cost_model.models.installation_cost_trajectory import InstallationCostTrajectory
from asf_lifetime_cost_model.models.subsidy_trajectory import SubsidyTrajectory

from asf_lifetime_cost_model import config

# %% [markdown]
# EnergyPriceTrajectory

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
# InstallationCostTrajectory

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
# SubsidyTrajectory

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
# HeatingSystem

# %%
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
gas_tdcv = 9_500  # kWh
heat_demand_uplift_with_heat_pump = 0.08
heat_demand_with_heat_pump = (9_500 * 0.85) * (1 + heat_demand_uplift_with_heat_pump)


# %%
heat_pump.calculate_annualised_lifetime_cost(
    heat_demand=heat_demand_with_heat_pump, energy_price_trajectory=electricity_prices
)

# %%
heat_pump.calculate_discounted_lifetime_cost(
    heat_demand=heat_demand_with_heat_pump, energy_price_trajectory=electricity_prices
)

# %%
heat_pump.calculate_annualised_discounted_lifetime_cost(
    heat_demand=heat_demand_with_heat_pump, energy_price_trajectory=electricity_prices
)

# %%
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
gas_boiler.calculate_annualised_lifetime_cost(heat_demand=heat_demand_with_boiler, energy_price_trajectory=gas_prices)

# %%
gas_boiler.calculate_discounted_lifetime_cost(heat_demand=heat_demand_with_boiler, energy_price_trajectory=gas_prices)

# %%
gas_boiler.calculate_annualised_discounted_lifetime_cost(
    heat_demand=heat_demand_with_boiler, energy_price_trajectory=gas_prices
)

# %% [markdown]
# Household

# %%
typical_household_boiler = Household(
    name="Typical household installing a gas boiler", heat_demand=heat_demand_with_boiler, heating_system=gas_boiler
)

typical_household_boiler.get_annualised_discounted_lifetime_cost(energy_price_trajectory=gas_prices)

# %%
typical_household_heat_pump = Household(
    name="Typical household installing an A2W HP", heat_demand=heat_demand_with_heat_pump, heating_system=heat_pump
)

typical_household_heat_pump.get_annualised_discounted_lifetime_cost(energy_price_trajectory=electricity_prices)
