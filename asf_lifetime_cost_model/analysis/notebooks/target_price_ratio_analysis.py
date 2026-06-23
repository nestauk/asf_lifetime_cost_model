# %%
import pandas as pd

import asf_lifetime_cost_model.getters.data_getters as data_getters

# %% [markdown]
# *Working in 2026 real £*
#
# **Heat pump lifetime cost formula**
#
# `ashp_lifetime_cost = (ashp_installation_cost - ashp_subsidy)
#                    + Σ[t=1 to ashp_lifetime] (ashp_energy_demand * electricity_price_t * discount_factor(t, r))`
#
# **Boiler lifetime cost formula**
#
# `boiler_lifetime_cost = boiler_installation_cost
#                      + Σ[t=1 to boiler_lifetime] ((boiler_energy_demand * gas_price_t) + gas_standing_charge) * discount_factor(t, r)`
#
# where `discount_factor(t, r) = 1 / (1 + r)^t`: `t` is years from installation, `r` is the real discount rate.
#
# **Analysis steps**
#
# For each installation year (2026-2035):
# - Set `ashp_lifetime_cost = boiler_lifetime_cost` with `electricity_price` unknown, solve for `electricity_price` and calculate `price_ratio`.
# - `ashp_subsidy` varies with installation year
# - `ashp_installation_cost` varies with installation year (-2.5% each year)
# - `gas_price` varies with operational years
# - `ashp_energy_demand` derived from `property_heat_demand` and `ashp_efficiency = 3.0`
# - No financing
# - Apply a ToU discount rate to price of electricity used for an ASHP
# - Assume 2% inflation rate
# - Assume real discount rate 3.5% (Green Book guidance)
# - `ashp_lifetime` and `boiler_lifetime` is 15 years
#

# %% [markdown]
# ----

# %%
# Time horizon
installation_years = range(2026, 2036)

# %% [markdown]
# ### Gas boiler

# %% [markdown]
# `boiler_installation_cost`

# %%
boiler_installation_cost_2026 = 3_000  # assumption, 2026 real £
# 0% real change — boiler costs flat in real terms
boiler_installation_costs = dict.fromkeys(installation_years, boiler_installation_cost_2026)

# %% [markdown]
# ### Air source heat pump

# %% [markdown]
# `ashp_installation_cost`

# %%
ashp_installation_cost_2026 = 13_100  # 2026 Q1, median cost of installation A2W heat pump, BUS statistics
nominal_reduction = 0.025  # assumption, 2.5% reduction in sticker price each year
inflation_rate = 0.02  # assumption

ashp_installation_costs = {}
ashp_installation_costs_nominal = {}

for year in installation_years:
    t = year - 2026

    nominal_cost = ashp_installation_cost_2026 * (1 - nominal_reduction) ** t  # cost reduction each year
    real_cost = (
        nominal_cost / (1 + inflation_rate) ** t
    )  # conversion to 2026 real £, adjust for inflation (shrink future money back into today's terms)

    ashp_installation_costs[year] = real_cost
    ashp_installation_costs_nominal[year] = nominal_cost

# %%
print(ashp_installation_costs_nominal)
print(ashp_installation_costs)

# %% [markdown]
# - Nominal installation costs: Declining only in market terms (no inflation adjustment).
# - Installation costs expressed in real 2026 £: same nominal prices adjusted for inflation, showing purchasing-power-adjusted costs in constant 2026 money.

# %% [markdown]
# `ashp_subsidy`

# %%
subsidy_df = data_getters.get_ashp_subsidy_options_data()
subsidy_df

# %%
# Subsidy scenario recommended in https://www.nesta.org.uk/report/delivering-clean-heat-a-policy-plan/
# now-2027: £7,500, 2028: £5,000, 2029-2030: £3,750: 2031-2033: £2,500, 2034 onwards: 0
# this is the "fast stepdown" subsidy scenario
subsidy_model = "fast stepdown"  # change this to switch scenarios
inflation_rate = 0.02
# get the row for chosen model, drop the 'model' column
subsidy_row = subsidy_df[subsidy_df["model"] == subsidy_model].drop(columns="model").iloc[0]
# map installation_year to subsidy value in 2026 real £
ashp_subsidy_levels = {
    year: subsidy_row[str(year)] / (1 + inflation_rate) ** (year - 2026) for year in installation_years
}
ashp_subsidy_levels_nominal = {year: subsidy_row[str(year)] for year in installation_years}

# %%
print(ashp_subsidy_levels)
print(ashp_subsidy_levels_nominal)

# %% [markdown]
# `ashp_efficiency`

# %%
# assume constant
ashp_efficiencies = dict.fromkeys(installation_years, 3.0)

# %% [markdown]
# ---


# %%
def solve_breakeven_electricity_price(
    property_heat_demand: float,  # kWh/year
    installation_year: int,
    ashp_efficiencies: dict[int, float],
    ashp_installation_costs: dict[int, float],  # £ (2026 real)
    ashp_subsidy_levels: dict[int, float],  # £ (2026 real)
    boiler_installation_costs: dict[int, float],  # £ (2026 real)
    boiler_efficiency: float,
    gas_price: float,  # £/kWh (2026 real)
    gas_standing_charge: float,  # £/year (2026 real)
    ashp_lifetime: int = 15,
    boiler_lifetime: int = 15,
    real_discount_rate: float = 0.035,
    tou_discount: float = 0.15,
) -> float:
    """Solve for the breakeven electricity price (£/kWh, 2026 real terms)
    at which an air-source heat pump (ASHP) and a gas boiler have equal
    discounted lifetime costs.

    The returned price is the standard-variable-tariff (SVT) electricity
    price before the time-of-use discount is applied.
    """
    # Annual energy demand
    ashp_energy_demand = property_heat_demand / ashp_efficiencies[installation_year]

    boiler_energy_demand = property_heat_demand / boiler_efficiency

    # Upfront costs
    ashp_capex = ashp_installation_costs[installation_year] - ashp_subsidy_levels[installation_year]

    boiler_capex = boiler_installation_costs[installation_year]

    # Boiler lifetime cost
    boiler_running_cost_pv = sum(
        (boiler_energy_demand * gas_price + gas_standing_charge) / (1 + real_discount_rate) ** t
        for t in range(1, boiler_lifetime + 1)
    )

    boiler_lifetime_cost = boiler_capex + boiler_running_cost_pv

    # Present-value factor for annual electricity expenditure
    electricity_cost_pv_factor = sum(
        ashp_energy_demand / (1 + real_discount_rate) ** t for t in range(1, ashp_lifetime + 1)
    )

    # Effective electricity price actually paid by the ASHP owner
    effective_electricity_price = (boiler_lifetime_cost - ashp_capex) / electricity_cost_pv_factor

    # Convert from effective ToU price to headline SVT price
    svt_electricity_price = effective_electricity_price / (1 - tou_discount)

    return svt_electricity_price


# %% [markdown]
# ## Results for Medium TDCV

# %%
# Assumptions for energy demand
medium_tdcv_gas = 11.5  # Medium Typical Domestic Consumption Value, used for energy price cap, MWh
# medium_tdcv_gas = 9.5  # Medium Typical Domestic Consumption Value, used for energy price cap, MWh

heating_gas_share = 0.97  # share of gas TDCV we are assuming is for heating
heat_demand = medium_tdcv_gas * heating_gas_share * 1000  # kWh/year

# %% [markdown]
# ### **April price cap gas prices**

# %% [markdown]
# Including gas standing charge

# %%
gas_price = 5.74 / 100  # £/kWh
gas_standing_charge = 29.09 / 100 * 365  # £/year

# %%
results = []

for installation_year in range(2026, 2036):
    subsidy = ashp_subsidy_levels[installation_year]
    gross_cost = ashp_installation_costs[installation_year]
    net_cost = gross_cost - subsidy

    electricity_price = solve_breakeven_electricity_price(
        property_heat_demand=heat_demand,
        installation_year=installation_year,
        ashp_efficiencies=ashp_efficiencies,
        ashp_installation_costs=ashp_installation_costs,
        ashp_subsidy_levels=ashp_subsidy_levels,
        boiler_installation_costs=boiler_installation_costs,
        boiler_efficiency=0.85,
        gas_price=gas_price,
        gas_standing_charge=gas_standing_charge,
        ashp_lifetime=15,
        boiler_lifetime=15,
        real_discount_rate=0.035,
        tou_discount=0.15,
    )

    ratio = electricity_price / gas_price

    results.append(
        {
            "installation_year": installation_year,
            "ashp_installation_cost": gross_cost,
            "subsidy": subsidy,
            "ashp_net_cost": net_cost,
            "breakeven_electricity_price": electricity_price,
            "electricity_gas_price_ratio": ratio,
        }
    )

results_df = pd.DataFrame(results)

# %%
results_df

# %% [markdown]
# Excluding gas standing charge

# %%
results = []

for installation_year in range(2026, 2036):
    subsidy = ashp_subsidy_levels[installation_year]
    gross_cost = ashp_installation_costs[installation_year]
    net_cost = gross_cost - subsidy

    electricity_price = solve_breakeven_electricity_price(
        property_heat_demand=heat_demand,
        installation_year=installation_year,
        ashp_efficiencies=ashp_efficiencies,
        ashp_installation_costs=ashp_installation_costs,
        ashp_subsidy_levels=ashp_subsidy_levels,
        boiler_installation_costs=boiler_installation_costs,
        boiler_efficiency=0.85,
        gas_price=gas_price,
        gas_standing_charge=0,  # EXCLUDED
        ashp_lifetime=15,
        boiler_lifetime=15,
        real_discount_rate=0.035,
        tou_discount=0.15,
    )

    ratio = electricity_price / gas_price

    results.append(
        {
            "installation_year": installation_year,
            "ashp_installation_cost": gross_cost,
            "subsidy": subsidy,
            "ashp_net_cost": net_cost,
            "breakeven_electricity_price": electricity_price,
            "electricity_gas_price_ratio": ratio,
        }
    )

results_df = pd.DataFrame(results)

# %%
results_df

# %% [markdown]
# ### **July price cap gas prices**

# %% [markdown]
# Including gas standing charge

# %%
gas_price = 7.33 / 100  # £/kWh
gas_standing_charge = 29.04 / 100 * 365  # £/year

# %%
results = []

for installation_year in range(2026, 2036):
    subsidy = ashp_subsidy_levels[installation_year]
    gross_cost = ashp_installation_costs[installation_year]
    net_cost = gross_cost - subsidy

    electricity_price = solve_breakeven_electricity_price(
        property_heat_demand=heat_demand,
        installation_year=installation_year,
        ashp_efficiencies=ashp_efficiencies,
        ashp_installation_costs=ashp_installation_costs,
        ashp_subsidy_levels=ashp_subsidy_levels,
        boiler_installation_costs=boiler_installation_costs,
        boiler_efficiency=0.85,
        gas_price=gas_price,
        gas_standing_charge=gas_standing_charge,
        ashp_lifetime=15,
        boiler_lifetime=15,
        real_discount_rate=0.035,
        tou_discount=0.15,
    )

    ratio = electricity_price / gas_price

    results.append(
        {
            "installation_year": installation_year,
            "ashp_installation_cost": gross_cost,
            "subsidy": subsidy,
            "ashp_net_cost": net_cost,
            "breakeven_electricity_price": electricity_price,
            "electricity_gas_price_ratio": ratio,
        }
    )

results_df = pd.DataFrame(results)

# %%
results_df

# %% [markdown]
# Excluding gas standing charge

# %%
results = []

for installation_year in range(2026, 2036):
    subsidy = ashp_subsidy_levels[installation_year]
    gross_cost = ashp_installation_costs[installation_year]
    net_cost = gross_cost - subsidy

    electricity_price = solve_breakeven_electricity_price(
        property_heat_demand=heat_demand,
        installation_year=installation_year,
        ashp_efficiencies=ashp_efficiencies,
        ashp_installation_costs=ashp_installation_costs,
        ashp_subsidy_levels=ashp_subsidy_levels,
        boiler_installation_costs=boiler_installation_costs,
        boiler_efficiency=0.85,
        gas_price=gas_price,
        gas_standing_charge=0,  # EXCLUDED
        ashp_lifetime=15,
        boiler_lifetime=15,
        real_discount_rate=0.035,
        tou_discount=0.15,
    )

    ratio = electricity_price / gas_price

    results.append(
        {
            "installation_year": installation_year,
            "ashp_installation_cost": gross_cost,
            "subsidy": subsidy,
            "ashp_net_cost": net_cost,
            "breakeven_electricity_price": electricity_price,
            "electricity_gas_price_ratio": ratio,
        }
    )

results_df = pd.DataFrame(results)

# %%
results_df
