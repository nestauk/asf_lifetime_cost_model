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
from asf_lifetime_cost_model.models.trajectory import (
    EnergyPriceTrajectory,
    InstallationCostTrajectory,
    SubsidyTrajectory,
)
from asf_lifetime_cost_model.models.heating_system import HeatingSystem

from asf_lifetime_cost_model import config

# %%
BASE_YEAR = 2026
INFLATION_RATE = config["default_inflation_rate"]
DISCOUNT_RATE = config["default_discount_rate"]  # 0.035, HMT Green Book

ASHP_EFFICIENCY = 3.0
ASHP_LIFESPAN = 15
ASHP_REAL_COST_REDUCTION = 0.025  # -2.5%/year real, from_year=2027
ASHP_SUBSIDY_SCENARIO = "fast stepdown"
ASHP_MAINTENANCE_COST_PER_VISIT = 80.0
ASHP_MAINTENANCE_FREQUENCY = 1.0

ASHP_HEAT_DEMAND_UPLIFT = 0

ASHP_INTEREST_RATE = 0.05
ASHP_LOAN_TERM = 10

ASHP_ELECTRICITY_TOU_TARIFF_DISCOUNT = 0.15  # 15% saving on unit rate, assumed for ASHP owners on a ToU tariff

BOILER_EFFICIENCY = 0.85
BOILER_LIFESPAN = 15
BOILER_INSTALLATION_COST_2026 = 3_000  # £, 2026 real, flat (0% real change)
BOILER_MAINTENANCE_COST_PER_VISIT = 80.0
BOILER_MAINTENANCE_FREQUENCY = 1.0

INSTALLATION_YEARS = range(config["install_start_year"], config["install_end_year"] + 1)

ASHP_SPACE_HEAT_DEMAND = 13_690  # kWh/year
ASHP_DOMESTIC_HOT_WATER_HEAT_DEMAND = 3_150  # kWh/year
ASHP_INSTALLATION_COST_2026 = 12_310  # £, 2026 real


# %% [markdown]
# ## EnergyPriceTrajectory

# %%
electricity_prices = EnergyPriceTrajectory(
    fuel="electricity",
    starting_price=data_getters.get_latest_price_cap_rate("electricity"),
    price_basis="real",
    base_year=BASE_YEAR,
)
# electricity_prices.set_trajectory(-0.02, from_year=2027)  # -2%/year, already in real terms
# electricity_prices.set_trajectory({2030: 10.0})  # explicit override example

electricity_prices

# %%
ashp_electricity_prices = EnergyPriceTrajectory(
    "electricity",
    starting_price=electricity_prices.get_price(year=BASE_YEAR),
    price_basis="real",
    base_year=BASE_YEAR,
)
ashp_electricity_prices.series = electricity_prices.prices.copy()
ashp_electricity_prices.apply_percentage_discount(ASHP_ELECTRICITY_TOU_TARIFF_DISCOUNT)
ashp_electricity_prices

# %%
gas_prices = EnergyPriceTrajectory(
    fuel="gas", starting_price=data_getters.get_latest_price_cap_rate("gas"), price_basis="real", base_year=BASE_YEAR
)
gas_prices

# %% [markdown]
# ## InstallationCostTrajectory

# %%
boiler_installation_costs = InstallationCostTrajectory(
    "gas_boiler",
    starting_cost=BOILER_INSTALLATION_COST_2026,
    price_basis="real",  # 3,000 is already stated in 2026 real £
    base_year=BASE_YEAR,
)
boiler_installation_costs
# no set_trajectory call needed
# the flat starting value across all years already represents "0% real change"

# %%
ashp_installation_costs = InstallationCostTrajectory(
    system_type="air_to_water_heat_pump",
    starting_cost=ASHP_INSTALLATION_COST_2026,
    price_basis="real",
    base_year=BASE_YEAR,
)
ashp_installation_costs.set_trajectory(-ASHP_REAL_COST_REDUCTION)
ashp_installation_costs

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
ashp_subsidies.to_real(base_year=BASE_YEAR, inflation_rate=INFLATION_RATE)
ashp_subsidies

# %% [markdown]
# ## HeatingSystem

# %% [markdown]
# **Heat pump - no financing**

# %%
# Heat pump
heat_pump = HeatingSystem(
    system_type="air_to_water_heat_pump",
    installation_year=2026,
    lifespan=ASHP_LIFESPAN,
    efficiency=ASHP_EFFICIENCY,
    installation_cost_trajectory=ashp_installation_costs,
    subsidy_trajectory=ashp_subsidies,
    maintenance_cost_per_visit=ASHP_MAINTENANCE_COST_PER_VISIT,
    maintenance_annual_frequency=ASHP_MAINTENANCE_FREQUENCY,  # annual maintenance
)
heat_pump

# %%
# Configure heat demand
heat_demand_with_heat_pump = ASHP_SPACE_HEAT_DEMAND + ASHP_DOMESTIC_HOT_WATER_HEAT_DEMAND


# %%
# discounted lifetime running cost for a chosen year
heat_pump.calculate_discounted_running_cost(
    year=2026, heat_demand=heat_demand_with_heat_pump, energy_price_trajectory=ashp_electricity_prices
)

# %%
# # error is raised if you try to get a running cost for a year that is outside its lifetime
# heat_pump.calculate_discounted_running_cost(
#     year=2045, heat_demand=heat_demand_with_heat_pump, energy_price_trajectory=electricity_prices
# )

# %%
# lifetime running cost
heat_pump.calculate_lifetime_running_cost(heat_demand_with_heat_pump, ashp_electricity_prices)

# %%
# discounted lifetime running cost
heat_pump.calculate_discounted_lifetime_running_cost(heat_demand_with_heat_pump, ashp_electricity_prices)

# %%
# capex (no financing)
heat_pump.calculate_lifetime_capital_cost()

# %%
# # raises error if you use a method related to loan interest/repayments
# heat_pump.calculate_annual_loan_repayment()

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
heat_pump.calculate_lifetime_cost(heat_demand_with_heat_pump, ashp_electricity_prices)

# %%
# annualised lifetime cost
heat_pump.calculate_annualised_lifetime_cost(heat_demand_with_heat_pump, ashp_electricity_prices)

# %%
# discounted lifetime cost
heat_pump.calculate_discounted_lifetime_cost(heat_demand_with_heat_pump, ashp_electricity_prices)

# %%
# discounted annualised lifetime cost
heat_pump.calculate_annualised_discounted_lifetime_cost(heat_demand_with_heat_pump, ashp_electricity_prices)

# %% [markdown]
# **Heat pump with financing**

# %%
# Heat pump financed
heat_pump_financed = HeatingSystem(
    system_type="air_to_water_heat_pump",
    installation_year=2026,
    lifespan=ASHP_LIFESPAN,
    efficiency=ASHP_EFFICIENCY,
    installation_cost_trajectory=ashp_installation_costs,
    subsidy_trajectory=ashp_subsidies,
    maintenance_cost_per_visit=ASHP_MAINTENANCE_COST_PER_VISIT,
    maintenance_annual_frequency=ASHP_MAINTENANCE_FREQUENCY,  # annual maintenance
    interest_rate=ASHP_INTEREST_RATE,
    loan_term=ASHP_LOAN_TERM,
)
heat_pump_financed

# %%
# annual loan repayment
heat_pump_financed.calculate_annual_loan_repayment()

# %%
# get discounted loan repayment for a given year
heat_pump_financed.calculate_discounted_loan_repayment(year=2027)

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
    heat_pump.capital_cost
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
    heat_pump.capital_cost
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
    lifespan=BOILER_LIFESPAN,
    efficiency=BOILER_EFFICIENCY,
    installation_cost_trajectory=boiler_installation_costs,
    subsidy_trajectory=gas_boiler_subsidies,
    maintenance_cost_per_visit=BOILER_MAINTENANCE_COST_PER_VISIT,
    maintenance_annual_frequency=BOILER_MAINTENANCE_FREQUENCY,
)

# %%
heat_demand_with_boiler = heat_demand_with_heat_pump / (1 + ASHP_HEAT_DEMAND_UPLIFT)

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
            heat_demand_with_heat_pump, ashp_electricity_prices
        ),
        "Total discounted lifetime cost": heat_pump.calculate_discounted_lifetime_cost(
            heat_demand_with_heat_pump, ashp_electricity_prices
        ),
        "Annualised discounted lifetime cost (EAC)": heat_pump.calculate_annualised_discounted_lifetime_cost(
            heat_demand_with_heat_pump, ashp_electricity_prices
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
            heat_demand_with_heat_pump, ashp_electricity_prices
        ),
        "Total discounted lifetime cost": heat_pump_financed.calculate_discounted_lifetime_cost(
            heat_demand_with_heat_pump, ashp_electricity_prices
        ),
        "Annualised discounted lifetime cost (EAC)": heat_pump_financed.calculate_annualised_discounted_lifetime_cost(
            heat_demand_with_heat_pump, ashp_electricity_prices
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

# %% [markdown]
# ### Cost parity methods

# %% [markdown]
# **Solving for subsidy**

# %%
# For one installation year

gas_boiler_eac = gas_boiler.calculate_annualised_discounted_lifetime_cost(
    heat_demand_with_boiler, gas_prices, gas_standing_charge
)

required_subsidy = heat_pump.solve_subsidy_for_parity(
    heat_demand=heat_demand_with_heat_pump,
    energy_price_trajectory=ashp_electricity_prices,
    target_eac=gas_boiler_eac,
)
print(
    f"Required subsidy for lifetime cost parity between ASHP vs gas boiler installed in {heat_pump.installation_year}: £{required_subsidy:,.2f}"
)

# %%
# Check
# Build a subsidy trajectory using the solved value, then a fresh HeatingSystem to verify against
verification_subsidy = SubsidyTrajectory(
    "air_to_water_heat_pump", starting_subsidy=required_subsidy, price_basis="real", base_year=2026
)

heat_pump_verified = HeatingSystem(
    system_type="air_to_water_heat_pump",
    installation_year=heat_pump.installation_year,
    lifespan=heat_pump.lifespan,
    efficiency=heat_pump.efficiency,
    installation_cost_trajectory=ashp_installation_costs,
    subsidy_trajectory=verification_subsidy,
    maintenance_cost_per_visit=heat_pump.maintenance_cost_per_visit,
    maintenance_annual_frequency=heat_pump.maintenance_annual_frequency,
)

verified_eac = heat_pump_verified.calculate_annualised_discounted_lifetime_cost(
    heat_demand=heat_demand_with_heat_pump,
    energy_price_trajectory=ashp_electricity_prices,
)

print(f"Gas boiler EAC (target):        £{gas_boiler_eac:,.2f}")
print(f"Heat pump EAC, solved subsidy:   £{verified_eac:,.2f}")
print(f"Match (within rounding):         {abs(verified_eac - gas_boiler_eac) < 0.01}")

# %% [markdown]
# **Solving for electricity price**

# %%
# For one installation year

gas_boiler_eac = gas_boiler.calculate_annualised_discounted_lifetime_cost(
    heat_demand_with_boiler, gas_prices, gas_standing_charge
)

required_ashp_electricity_prices = heat_pump.solve_electricity_price_for_parity(
    heat_demand=heat_demand_with_heat_pump,
    energy_price_trajectory=ashp_electricity_prices,
    target_eac=gas_boiler_eac,
)

required_price_cap_rates = {
    year: effective_price / (1 - ASHP_ELECTRICITY_TOU_TARIFF_DISCOUNT)
    for year, effective_price in required_ashp_electricity_prices.items()
}

required_price_cap_rates

# %%
# Check

# Build a real trajectory using the solved per-year prices
verification_trajectory = EnergyPriceTrajectory(
    "electricity",
    starting_price=required_price_cap_rates[heat_pump.installation_year],
    price_basis="real",
    base_year=2026,
)
for year, price in required_price_cap_rates.items():
    verification_trajectory.prices.loc[year] = price * (1 - ASHP_ELECTRICITY_TOU_TARIFF_DISCOUNT)

# Recompute EAC using that trajectory, entirely independently of the solver
verified_eac = heat_pump.calculate_annualised_discounted_lifetime_cost(
    heat_demand=heat_demand_with_heat_pump,
    energy_price_trajectory=verification_trajectory,
)

print(f"Gas boiler EAC (target):                £{gas_boiler_eac:,.2f}")
print(f"Heat pump EAC, solved price trajectory:  £{verified_eac:,.2f}")
print(f"Match (within rounding):                 {abs(verified_eac - gas_boiler_eac) < 0.01}")

# %%
required_price_ratios = {
    year: required_price_cap_rates[year] / gas_prices.get_price(year=year) for year in required_price_cap_rates
}
required_price_ratios

# %% [markdown]
# For all installation years

# %%
INSTALLATION_YEARS = range(config["install_start_year"], config["install_end_year"] + 1)

required_subsidy_by_year = {}

for installation_year in INSTALLATION_YEARS:
    heat_pump = HeatingSystem(
        system_type="air_to_water_heat_pump",
        installation_year=installation_year,
        lifespan=15,
        efficiency=3.0,
        installation_cost_trajectory=ashp_installation_costs,
        subsidy_trajectory=ashp_subsidies,  # zero-subsidy baseline system
        maintenance_cost_per_visit=80.0,
        maintenance_annual_frequency=1.0,
    )
    gas_boiler = HeatingSystem(
        system_type="gas_boiler",
        installation_year=installation_year,
        lifespan=15,
        efficiency=0.85,
        installation_cost_trajectory=boiler_installation_costs,
        subsidy_trajectory=gas_boiler_subsidies,
        maintenance_cost_per_visit=80.0,
        maintenance_annual_frequency=1.0,
    )

    gas_boiler_eac = gas_boiler.calculate_annualised_discounted_lifetime_cost(
        heat_demand=heat_demand_with_boiler, energy_price_trajectory=gas_prices, standing_charge=gas_standing_charge
    )

    required_subsidy_by_year[installation_year] = heat_pump.solve_subsidy_for_parity(
        heat_demand=heat_demand_with_heat_pump,
        energy_price_trajectory=ashp_electricity_prices,
        target_eac=gas_boiler_eac,
    )

required_subsidy_by_year

# %%
required_subsidy_trajectory = SubsidyTrajectory(
    "air_to_water_heat_pump",
    starting_subsidy=required_subsidy_by_year[config["install_start_year"]],
    price_basis="real",
    base_year=2026,
)
required_subsidy_trajectory.set_trajectory(required_subsidy_by_year)

required_subsidy_trajectory

# %%
INSTALLATION_YEARS = range(config["install_start_year"], config["install_end_year"] + 1)

price_ratio_rows = []
scale_factor_by_installation_year = {}

for installation_year in INSTALLATION_YEARS:
    heat_pump = HeatingSystem(
        system_type="air_to_water_heat_pump",
        installation_year=installation_year,
        lifespan=15,
        efficiency=3.0,
        installation_cost_trajectory=ashp_installation_costs,
        subsidy_trajectory=ashp_subsidies,
        maintenance_cost_per_visit=80.0,
        maintenance_annual_frequency=1.0,
    )
    gas_boiler = HeatingSystem(
        system_type="gas_boiler",
        installation_year=installation_year,
        lifespan=15,
        efficiency=0.85,
        installation_cost_trajectory=boiler_installation_costs,
        subsidy_trajectory=gas_boiler_subsidies,
        maintenance_cost_per_visit=80.0,
        maintenance_annual_frequency=1.0,
    )

    gas_boiler_eac = gas_boiler.calculate_annualised_discounted_lifetime_cost(
        heat_demand=heat_demand_with_boiler, energy_price_trajectory=gas_prices, standing_charge=gas_standing_charge
    )

    required_ashp_electricity_prices = heat_pump.solve_electricity_price_for_parity(
        heat_demand=heat_demand_with_heat_pump,
        energy_price_trajectory=ashp_electricity_prices,
        target_eac=gas_boiler_eac,
    )

    required_price_cap_rates = {
        year: effective_price / (1 - ASHP_ELECTRICITY_TOU_TARIFF_DISCOUNT)
        for year, effective_price in required_ashp_electricity_prices.items()
    }

    scale_factor_by_installation_year[installation_year] = required_price_cap_rates[
        installation_year
    ] / electricity_prices.get_price(year=installation_year)

    for operating_year, required_price in required_price_cap_rates.items():
        price_ratio_rows.append(
            {
                "installation_year": installation_year,
                "operating_year": operating_year,
                "required_electricity_price": required_price,
                "gas_price": gas_prices.get_price(year=operating_year),
                "price_ratio": required_price / gas_prices.get_price(year=operating_year),
            }
        )

price_ratio_df = pd.DataFrame(price_ratio_rows)


# %%
# Pivot: rows = operating year, columns = installation year, values = required electricity price
required_price_pivot = price_ratio_df.pivot(
    index="operating_year", columns="installation_year", values="required_electricity_price"
)

scale_factor_row = pd.Series(scale_factor_by_installation_year, name="Scale factor (k)")
required_price_pivot = pd.concat([required_price_pivot, scale_factor_row.to_frame().T])

required_price_pivot

# %%
