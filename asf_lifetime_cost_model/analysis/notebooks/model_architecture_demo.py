# %%
import asf_lifetime_cost_model.getters.data_getters as data_getters
from asf_lifetime_cost_model.models.energy_price_trajectory import EnergyPriceTrajectory
from asf_lifetime_cost_model.models.heating_system import HeatingSystem
from asf_lifetime_cost_model.models.household import Household
from asf_lifetime_cost_model.models.installation_cost_trajectory import InstallationCostTrajectory
from asf_lifetime_cost_model.models.subsidy_trajectory import SubsidyTrajectory

# %% [markdown]
# EnergyPriceTrajectory

# %%
# usage
electricity_prices = EnergyPriceTrajectory(
    fuel="electricity", starting_price=data_getters.get_latest_price_cap_rate("electricity")
)
gas_prices = EnergyPriceTrajectory(fuel="gas", starting_price=data_getters.get_latest_price_cap_rate("gas"))

# electricity_prices.set_trajectory(-0.02, from_year=2027)  # -2% change from 2027
# electricity_prices.set_trajectory({2030: 10.0})  # explicit override

electricity_prices

# %% [markdown]
# InstallationCostTrajectory

# %%
gas_boiler_installation_costs = InstallationCostTrajectory(system_type="gas_boiler", starting_cost=3_500)

# %%
ashp_installation_costs = InstallationCostTrajectory(system_type="air_to_water_heat_pump", starting_cost=12_500)
ashp_installation_costs.set_trajectory(-0.02)
ashp_installation_costs

# %% [markdown]
# SubsidyTrajectory

# %%
ashp_subsidies = SubsidyTrajectory(system_type="air_to_water_heat_pump", starting_subsidy=7_500)

# %%
# example setting trajectory to one of subsidy pathway options
subsidy_options = data_getters.get_ashp_subsidy_options_data()
fast_stepdown_row = subsidy_options.set_index("model").loc["fast stepdown"]
fast_stepdown_values = {
    int(year): value for year, value in fast_stepdown_row.items() if int(year) in ashp_subsidies.subsidy.index
}
ashp_subsidies.set_trajectory(fast_stepdown_values)

ashp_subsidies

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
heat_pump.calculate_annualised_lifetime_cost(heat_demand=13_500, energy_price_trajectory=electricity_prices)

# %%
gas_boiler_subsidies = SubsidyTrajectory(system_type="gas_boiler", starting_subsidy=0.0)

gas_boiler = HeatingSystem(
    system_type="gas_boiler",
    installation_year=2026,
    lifespan=15,
    efficiency=0.85,
    installation_cost_trajectory=gas_boiler_installation_costs,
    subsidy_trajectory=gas_boiler_subsidies,
    maintenance_cost_per_visit=80.0,
    maintenance_annual_frequency=1.0,
)

# %%
gas_boiler.calculate_annualised_lifetime_cost(heat_demand=13_500 / 1.08, energy_price_trajectory=gas_prices)

# %% [markdown]
# Household

# %%
# usage
typical_household_hp = Household(
    name="Typical household installing an A2W HP", heat_demand=13_500, heating_system=heat_pump
)

typical_household_hp.get_annualised_lifetime_cost(energy_price_trajectory=electricity_prices)

# %%
typical_household_boiler = Household(
    name="Typical household installing a gas boiler", heat_demand=13_500 / 1.08, heating_system=gas_boiler
)

typical_household_boiler.get_annualised_lifetime_cost(energy_price_trajectory=gas_prices)
