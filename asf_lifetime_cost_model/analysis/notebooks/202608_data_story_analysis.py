# %%
import pandas as pd

import asf_lifetime_cost_model.getters.data_getters as data_getters
from asf_lifetime_cost_model import config
from asf_lifetime_cost_model.models.heating_system import HeatingSystem
from asf_lifetime_cost_model.models.trajectory import (
    EnergyPriceTrajectory,
    InstallationCostTrajectory,
    SubsidyTrajectory,
)

# %%
# Baseline assumptions that are intended to reflect business-as-usual scenario
BASE_YEAR = 2026
INFLATION_RATE = config["default_inflation_rate"]
DISCOUNT_RATE = config["default_discount_rate"]  # 0.035, HMT Green Book

ASHP_EFFICIENCY = 3.0
ASHP_LIFESPAN = 15
ASHP_REAL_COST_REDUCTION = 0.025  # -2.5%/year real, from_year=2027
ASHP_SUBSIDY_SCENARIO = "flat"
ASHP_MAINTENANCE_COST_PER_VISIT = 80.0
ASHP_MAINTENANCE_FREQUENCY = 1.0

ASHP_HEAT_DEMAND_UPLIFT = 0

ASHP_INTEREST_RATE = 0.05
ASHP_LOAN_TERM = 10

BOILER_EFFICIENCY = 0.85
BOILER_LIFESPAN = 15
BOILER_INSTALLATION_COST_2026 = 3_000  # £, 2026 real, flat (0% real change)
BOILER_MAINTENANCE_COST_PER_VISIT = 80.0
BOILER_MAINTENANCE_FREQUENCY = 1.0

INSTALLATION_YEARS = range(config["install_start_year"], config["install_end_year"] + 1)

# From MCS analysis
ASHP_SPACE_HEAT_DEMAND = 13_668  # kWh/year, average home fitting an 8-10 kW heat pump FY 2025/26
ASHP_DOMESTIC_HOT_WATER_HEAT_DEMAND = 3_155  # kWh/year, average home fitting an 8-10 kW heat pump FY 2025/26
ASHP_INSTALLATION_COST_2026 = 12_500.0  # £, average home fitting an 8-10 kW heat pump FY 2025/26

# %%
13_668 + 3_155


# %%
def compare_heating_systems(
    heat_pump_scenario: str,
    heat_pump: HeatingSystem,
    gas_boiler: HeatingSystem,
    ashp_electricity_prices: EnergyPriceTrajectory,
    gas_prices: EnergyPriceTrajectory,
    gas_standing_charge: float,
    heat_demand_with_heat_pump: float,
    heat_demand_with_gas_boiler: float,
):

    heat_pump_installation_cost = heat_pump.calculate_annualised_discounted_lifetime_capital_cost()
    heat_pump_running_cost = heat_pump.calculate_annualised_discounted_lifetime_running_cost(
        heat_demand=heat_demand_with_heat_pump, energy_price_trajectory=ashp_electricity_prices
    )
    heat_pump_maintenance_cost = heat_pump.calculate_annualised_discounted_lifetime_maintenance_cost()
    heat_pump_total_cost = heat_pump.calculate_annualised_discounted_lifetime_cost(
        heat_demand=heat_demand_with_heat_pump, energy_price_trajectory=ashp_electricity_prices
    )

    gas_boiler_installation_cost = gas_boiler.calculate_annualised_discounted_lifetime_capital_cost()
    gas_boiler_running_cost = gas_boiler.calculate_annualised_discounted_lifetime_running_cost(
        heat_demand=heat_demand_with_gas_boiler, energy_price_trajectory=gas_prices, standing_charge=gas_standing_charge
    )
    gas_boiler_maintenance_cost = gas_boiler.calculate_annualised_discounted_lifetime_maintenance_cost()
    gas_boiler_total_cost = gas_boiler.calculate_annualised_discounted_lifetime_cost(
        heat_demand=heat_demand_with_gas_boiler,
        energy_price_trajectory=gas_prices,
        standing_charge=gas_standing_charge,
    )

    lifetime_cost_comparison = pd.DataFrame(
        {
            "Gas boiler": {
                "Installation cost": gas_boiler_installation_cost,
                "Running cost": gas_boiler_running_cost,
                "Maintenance cost": gas_boiler_maintenance_cost,
                "Total annualised lifetime cost": gas_boiler_total_cost,
                "EAC gap": gas_boiler_total_cost - gas_boiler_total_cost,
            },
            heat_pump_scenario: {
                "Installation cost": heat_pump_installation_cost,
                "Running cost": heat_pump_running_cost,
                "Maintenance cost": heat_pump_maintenance_cost,
                "Total annualised lifetime cost": heat_pump_total_cost,
                "EAC gap": heat_pump_total_cost - gas_boiler_total_cost,
            },
        }
    )
    return lifetime_cost_comparison.map(lambda value: f"£{value:,.2f}/year")


# %% [markdown]
# 1. Baseline scenario

# %%
# Energy prices
electricity_prices = EnergyPriceTrajectory(
    fuel="electricity",
    starting_price=data_getters.get_latest_price_cap_rate("electricity"),
    price_basis="real",
    base_year=BASE_YEAR,
)  # held flat at current

gas_prices = EnergyPriceTrajectory(
    fuel="gas", starting_price=data_getters.get_latest_price_cap_rate("gas"), price_basis="real", base_year=BASE_YEAR
)  # held flat at current

gas_standing_charge = data_getters.get_latest_price_cap_standing_charge(fuel="gas")

# %%
# Installation cost trajectory
ashp_installation_costs = InstallationCostTrajectory(
    system_type="air_to_water_heat_pump",
    starting_cost=ASHP_INSTALLATION_COST_2026,
    price_basis="real",
    base_year=BASE_YEAR,
)
ashp_installation_costs.set_trajectory(-ASHP_REAL_COST_REDUCTION)

boiler_installation_costs = InstallationCostTrajectory(
    "gas_boiler",
    starting_cost=BOILER_INSTALLATION_COST_2026,
    price_basis="real",  # 3,000 is already stated in 2026 real £
    base_year=BASE_YEAR,
)

# %%
# Subsidy trajectory, default is flat
ashp_subsidies = SubsidyTrajectory(system_type="air_to_water_heat_pump", starting_subsidy=7_500, price_basis="nominal")
ashp_subsidies.to_real(base_year=BASE_YEAR, inflation_rate=INFLATION_RATE)

gas_boiler_subsidies = SubsidyTrajectory(
    system_type="gas_boiler", starting_subsidy=0.0, price_basis="real", base_year=BASE_YEAR
)

# %%
# Heat demand
heat_demand_with_heat_pump = ASHP_SPACE_HEAT_DEMAND + ASHP_DOMESTIC_HOT_WATER_HEAT_DEMAND
heat_demand_with_gas_boiler = heat_demand_with_heat_pump / (1 + ASHP_HEAT_DEMAND_UPLIFT)

# %%
# Baseline heat pump
heat_pump_bau = HeatingSystem(
    system_type="air_to_water_heat_pump",
    installation_year=2026,
    lifespan=ASHP_LIFESPAN,
    efficiency=ASHP_EFFICIENCY,
    installation_cost_trajectory=ashp_installation_costs,
    subsidy_trajectory=ashp_subsidies,
    maintenance_cost_per_visit=ASHP_MAINTENANCE_COST_PER_VISIT,
    maintenance_annual_frequency=ASHP_MAINTENANCE_FREQUENCY,
)

# Baseline gas boiler (doesn't change across scenarios)
gas_boiler = HeatingSystem(
    system_type="gas_boiler",
    installation_year=BASE_YEAR,
    lifespan=BOILER_LIFESPAN,
    efficiency=BOILER_EFFICIENCY,
    installation_cost_trajectory=boiler_installation_costs,
    subsidy_trajectory=gas_boiler_subsidies,
    maintenance_cost_per_visit=BOILER_MAINTENANCE_COST_PER_VISIT,
    maintenance_annual_frequency=BOILER_MAINTENANCE_FREQUENCY,
)

# %%
compare_heating_systems(
    heat_pump_scenario="Heat pump (BAU)",
    heat_pump=heat_pump_bau,
    gas_boiler=gas_boiler,
    ashp_electricity_prices=electricity_prices,
    gas_prices=gas_prices,
    gas_standing_charge=0,
    heat_demand_with_heat_pump=heat_demand_with_heat_pump,
    heat_demand_with_gas_boiler=heat_demand_with_gas_boiler,
)

# %% [markdown]
# Scenario: Lower electricity-gas price ratio (1)

# %%
target_price_ratio = 2.9

gas_price = gas_prices.get_price(2026)
target_electricity_price = target_price_ratio * gas_price

electricity_prices_target_ratio = EnergyPriceTrajectory(
    fuel="electricity",
    starting_price=target_electricity_price,
    price_basis="real",
    base_year=BASE_YEAR,
)  # held flat

# %%
target_electricity_price

# %%
compare_heating_systems(
    heat_pump_scenario="Heat pump (Electricity prices for 2.9 target ratio)",
    heat_pump=heat_pump_bau,
    gas_boiler=gas_boiler,
    ashp_electricity_prices=electricity_prices_target_ratio,
    gas_prices=gas_prices,
    gas_standing_charge=0,
    heat_demand_with_heat_pump=heat_demand_with_heat_pump,
    heat_demand_with_gas_boiler=heat_demand_with_gas_boiler,
)

# %% [markdown]
# Scenario: Lower electricity-gas price ratio (2)

# %%
gas_prices_pre_iran = EnergyPriceTrajectory(fuel="gas", starting_price=5.74, price_basis="real", base_year=BASE_YEAR)
target_electricity_price_pre_iran = target_price_ratio * 5.74

electricity_prices_target_ratio_pre_iran = EnergyPriceTrajectory(
    fuel="electricity",
    starting_price=target_electricity_price_pre_iran,
    price_basis="real",
    base_year=BASE_YEAR,
)  # held flat

target_electricity_price_pre_iran

# %%
compare_heating_systems(
    heat_pump_scenario="Heat pump (Electricity prices for 2.9 target ratio)",
    heat_pump=heat_pump_bau,
    gas_boiler=gas_boiler,
    ashp_electricity_prices=electricity_prices_target_ratio_pre_iran,
    gas_prices=gas_prices_pre_iran,
    gas_standing_charge=0,
    heat_demand_with_heat_pump=heat_demand_with_heat_pump,
    heat_demand_with_gas_boiler=heat_demand_with_gas_boiler,
)

# %% [markdown]
# Sub-scenario: Lower heat demand

# %%
MEDIUM_GAS_TDCV = 9_500  # kWh/year
GAS_SHARE_FOR_HEATING = 0.97
MEDIUM_ELECTRICITY_TDCV = 2_500  # kWh/year

tdcv_heat_demand_with_gas_boiler = (MEDIUM_GAS_TDCV * GAS_SHARE_FOR_HEATING) * BOILER_EFFICIENCY
tdcv_heat_demand_with_heat_pump = tdcv_heat_demand_with_gas_boiler * (1 + ASHP_HEAT_DEMAND_UPLIFT)

# %%
tdcv_heat_demand_with_gas_boiler

# %%
compare_heating_systems(
    heat_pump_scenario="Heat pump (BAU)",
    heat_pump=heat_pump_bau,
    gas_boiler=gas_boiler,
    ashp_electricity_prices=electricity_prices,
    gas_prices=gas_prices,
    gas_standing_charge=0,
    heat_demand_with_heat_pump=tdcv_heat_demand_with_heat_pump,
    heat_demand_with_gas_boiler=tdcv_heat_demand_with_gas_boiler,
)

# %%
compare_heating_systems(
    heat_pump_scenario="Heat pump (Medium TDCV)",
    heat_pump=heat_pump_bau,
    gas_boiler=gas_boiler,
    ashp_electricity_prices=electricity_prices_target_ratio,
    gas_prices=gas_prices,
    gas_standing_charge=0,
    heat_demand_with_heat_pump=tdcv_heat_demand_with_heat_pump,
    heat_demand_with_gas_boiler=tdcv_heat_demand_with_gas_boiler,
)

# %% [markdown]
# Scenario: Heat pump high efficiency (1)

# %%
heat_pump_high_scop = HeatingSystem(
    system_type="air_to_water_heat_pump",
    installation_year=2026,
    lifespan=ASHP_LIFESPAN,
    efficiency=3.8,
    installation_cost_trajectory=ashp_installation_costs,
    subsidy_trajectory=ashp_subsidies,
    maintenance_cost_per_visit=ASHP_MAINTENANCE_COST_PER_VISIT,
    maintenance_annual_frequency=ASHP_MAINTENANCE_FREQUENCY,
)

# %%
compare_heating_systems(
    heat_pump_scenario="Heat pump (3.8 SCOP)",
    heat_pump=heat_pump_high_scop,
    gas_boiler=gas_boiler,
    ashp_electricity_prices=electricity_prices,
    gas_prices=gas_prices,
    gas_standing_charge=0,
    heat_demand_with_heat_pump=heat_demand_with_heat_pump,
    heat_demand_with_gas_boiler=heat_demand_with_gas_boiler,
)

# %% [markdown]
# Scenario: Heat pump low efficiency (2)

# %%
heat_pump_low_scop = HeatingSystem(
    system_type="air_to_water_heat_pump",
    installation_year=2026,
    lifespan=ASHP_LIFESPAN,
    efficiency=2.8,
    installation_cost_trajectory=ashp_installation_costs,
    subsidy_trajectory=ashp_subsidies,
    maintenance_cost_per_visit=ASHP_MAINTENANCE_COST_PER_VISIT,
    maintenance_annual_frequency=ASHP_MAINTENANCE_FREQUENCY,
)

# %%
compare_heating_systems(
    heat_pump_scenario="Heat pump (2.8 SCOP)",
    heat_pump=heat_pump_low_scop,
    gas_boiler=gas_boiler,
    ashp_electricity_prices=electricity_prices,
    gas_prices=gas_prices,
    gas_standing_charge=0,
    heat_demand_with_heat_pump=heat_demand_with_heat_pump,
    heat_demand_with_gas_boiler=heat_demand_with_gas_boiler,
)

# %% [markdown]
# Scenario: Including gas standing charge

# %%
compare_heating_systems(
    heat_pump_scenario="Heat pump (BAU)",
    heat_pump=heat_pump_bau,
    gas_boiler=gas_boiler,
    ashp_electricity_prices=electricity_prices,
    gas_prices=gas_prices,
    gas_standing_charge=gas_standing_charge,
    heat_demand_with_heat_pump=heat_demand_with_heat_pump,
    heat_demand_with_gas_boiler=heat_demand_with_gas_boiler,
)

# %% [markdown]
# Scenario: Longer lifespan

# %%
heat_pump_long_life = HeatingSystem(
    system_type="air_to_water_heat_pump",
    installation_year=2026,
    lifespan=20,
    efficiency=ASHP_EFFICIENCY,
    installation_cost_trajectory=ashp_installation_costs,
    subsidy_trajectory=ashp_subsidies,
    maintenance_cost_per_visit=ASHP_MAINTENANCE_COST_PER_VISIT,
    maintenance_annual_frequency=ASHP_MAINTENANCE_FREQUENCY,
)

# %%
compare_heating_systems(
    heat_pump_scenario="Heat pump (20-yr lifespan)",
    heat_pump=heat_pump_long_life,
    gas_boiler=gas_boiler,
    ashp_electricity_prices=electricity_prices,
    gas_prices=gas_prices,
    gas_standing_charge=gas_standing_charge,
    heat_demand_with_heat_pump=heat_demand_with_heat_pump,
    heat_demand_with_gas_boiler=heat_demand_with_gas_boiler,
)

# %% [markdown]
# Scenario: Installation costs

# %%
# suppose 2026 installation cost is 10% cheaper
ashp_installation_costs_discounted = InstallationCostTrajectory(
    "air_to_water_heat_pump",
    starting_cost=ASHP_INSTALLATION_COST_2026 * 0.9,
    price_basis=ashp_installation_costs.price_basis,
    base_year=ashp_installation_costs.base_year,
)

# %%
heat_pump_cheaper_install = HeatingSystem(
    system_type="air_to_water_heat_pump",
    installation_year=2026,
    lifespan=ASHP_LIFESPAN,
    efficiency=ASHP_EFFICIENCY,
    installation_cost_trajectory=ashp_installation_costs_discounted,
    subsidy_trajectory=ashp_subsidies,
    maintenance_cost_per_visit=ASHP_MAINTENANCE_COST_PER_VISIT,
    maintenance_annual_frequency=ASHP_MAINTENANCE_FREQUENCY,
)

# %%
compare_heating_systems(
    heat_pump_scenario="Heat pump (cheaper install cost)",
    heat_pump=heat_pump_cheaper_install,
    gas_boiler=gas_boiler,
    ashp_electricity_prices=electricity_prices,
    gas_prices=gas_prices,
    gas_standing_charge=0,
    heat_demand_with_heat_pump=heat_demand_with_heat_pump,
    heat_demand_with_gas_boiler=heat_demand_with_gas_boiler,
)

# %%
ASHP_INSTALLATION_COST_2026 * 0.9

# %% [markdown]
# Scenario: Subsidy

# %%
ashp_subsidies_zero = SubsidyTrajectory(
    "air_to_water_heat_pump", starting_subsidy=0.0, price_basis="real", base_year=BASE_YEAR
)

# %%
heat_pump_no_subsidy = HeatingSystem(
    system_type="air_to_water_heat_pump",
    installation_year=2026,
    lifespan=ASHP_LIFESPAN,
    efficiency=ASHP_EFFICIENCY,
    installation_cost_trajectory=ashp_installation_costs,
    subsidy_trajectory=ashp_subsidies_zero,
    maintenance_cost_per_visit=ASHP_MAINTENANCE_COST_PER_VISIT,
    maintenance_annual_frequency=ASHP_MAINTENANCE_FREQUENCY,
)

# %%
compare_heating_systems(
    heat_pump_scenario="Heat pump (zero subsidy)",
    heat_pump=heat_pump_no_subsidy,
    gas_boiler=gas_boiler,
    ashp_electricity_prices=electricity_prices,
    gas_prices=gas_prices,
    gas_standing_charge=0,
    heat_demand_with_heat_pump=heat_demand_with_heat_pump,
    heat_demand_with_gas_boiler=heat_demand_with_gas_boiler,
)

# %% [markdown]
# Scenario: Finance

# %%
heat_pump_financed = HeatingSystem(
    system_type="air_to_water_heat_pump",
    installation_year=2026,
    lifespan=ASHP_LIFESPAN,
    efficiency=ASHP_EFFICIENCY,
    installation_cost_trajectory=ashp_installation_costs,
    subsidy_trajectory=ashp_subsidies,
    maintenance_cost_per_visit=ASHP_MAINTENANCE_COST_PER_VISIT,
    maintenance_annual_frequency=ASHP_MAINTENANCE_FREQUENCY,
    interest_rate=ASHP_INTEREST_RATE,
    loan_term=ASHP_LOAN_TERM,
)

# %%
compare_heating_systems(
    heat_pump_scenario="Heat pump (5% interest rate, 10 year loan)",
    heat_pump=heat_pump_financed,
    gas_boiler=gas_boiler,
    ashp_electricity_prices=electricity_prices,
    gas_prices=gas_prices,
    gas_standing_charge=0,
    heat_demand_with_heat_pump=heat_demand_with_heat_pump,
    heat_demand_with_gas_boiler=heat_demand_with_gas_boiler,
)

# %% [markdown]
# Scenario: Electricity tariff

# %%
electricity_prices_discounted_low = EnergyPriceTrajectory(
    "electricity",
    starting_price=electricity_prices.get_price(year=BASE_YEAR),
    price_basis="real",
    base_year=BASE_YEAR,
)
electricity_prices_discounted_low.series = electricity_prices.prices.copy()
electricity_prices_discounted_low.apply_percentage_discount(0.15)

# %%
electricity_prices_discounted_high = EnergyPriceTrajectory(
    "electricity",
    starting_price=electricity_prices.get_price(year=BASE_YEAR),
    price_basis="real",
    base_year=BASE_YEAR,
)
electricity_prices_discounted_high.series = electricity_prices.prices.copy()
electricity_prices_discounted_high.apply_percentage_discount(0.30)

# %%
compare_heating_systems(
    heat_pump_scenario="Heat pump (15% ToU)",
    heat_pump=heat_pump_bau,
    gas_boiler=gas_boiler,
    ashp_electricity_prices=electricity_prices_discounted_low,
    gas_prices=gas_prices,
    gas_standing_charge=0,
    heat_demand_with_heat_pump=heat_demand_with_heat_pump,
    heat_demand_with_gas_boiler=heat_demand_with_gas_boiler,
)

# %%
compare_heating_systems(
    heat_pump_scenario="Heat pump (30% ToU)",
    heat_pump=heat_pump_bau,
    gas_boiler=gas_boiler,
    ashp_electricity_prices=electricity_prices_discounted_high,
    gas_prices=gas_prices,
    gas_standing_charge=0,
    heat_demand_with_heat_pump=heat_demand_with_heat_pump,
    heat_demand_with_gas_boiler=heat_demand_with_gas_boiler,
)

# %% [markdown]
# Scenario: Everything

# %%
heat_pump_optimal = HeatingSystem(
    system_type="air_to_water_heat_pump",
    installation_year=2026,
    lifespan=20,
    efficiency=3.8,
    installation_cost_trajectory=ashp_installation_costs_discounted,
    subsidy_trajectory=ashp_subsidies,
    maintenance_cost_per_visit=ASHP_MAINTENANCE_COST_PER_VISIT,
    maintenance_annual_frequency=ASHP_MAINTENANCE_FREQUENCY,
)

# %%
electricity_prices_discounted_low_target_ratio = EnergyPriceTrajectory(
    "electricity",
    starting_price=electricity_prices_target_ratio.get_price(year=BASE_YEAR),
    price_basis="real",
    base_year=BASE_YEAR,
)
electricity_prices_discounted_low_target_ratio.series = electricity_prices_target_ratio.prices.copy()
electricity_prices_discounted_low_target_ratio.apply_percentage_discount(0.15)

# %%
electricity_prices_discounted_low_target_ratio

# %%
electricity_prices_target_ratio

# %%
compare_heating_systems(
    heat_pump_scenario="Heat pump (combined)",
    heat_pump=heat_pump_optimal,
    gas_boiler=gas_boiler,
    ashp_electricity_prices=electricity_prices_discounted_low_target_ratio,
    gas_prices=gas_prices,
    gas_standing_charge=gas_standing_charge,
    heat_demand_with_heat_pump=heat_demand_with_heat_pump,
    heat_demand_with_gas_boiler=heat_demand_with_gas_boiler,
)

# %%
