"""Script to produce lifetime cost comparison for a typical household, with default assumptions.

Compares an air-source heat pump (with several variants: subsidised, financed,
no subsidy) against a gas boiler (with/without standing charge), for
installation in every year 2026-2035. Outputs an Excel workbook (Summary,
Comparison, Annual breakdown tabs) and several plots.

Run by entering `uv run python asf_lifetime_cost_model/analysis/typical_household.py` in the terminal.
"""

from pathlib import Path

import altair as alt
import pandas as pd

import asf_lifetime_cost_model.getters.data_getters as data_getters
from asf_lifetime_cost_model import config
from asf_lifetime_cost_model.models.energy_price_trajectory import EnergyPriceTrajectory
from asf_lifetime_cost_model.models.heating_system import HeatingSystem
from asf_lifetime_cost_model.models.installation_cost_trajectory import InstallationCostTrajectory
from asf_lifetime_cost_model.models.subsidy_trajectory import SubsidyTrajectory

alt.data_transformers.disable_max_rows()  # comparison_df/annual_breakdown_df can exceed Altair's default 5000-row cap

# ---------------------------------------------------------------------------
# Assumptions
# ---------------------------------------------------------------------------
BASE_YEAR = 2026
INFLATION_RATE = 0.02
DISCOUNT_RATE = config["default_discount_rate"]  # 0.035, HMT Green Book

ASHP_EFFICIENCY = 3.0
ASHP_LIFESPAN = 15
ASHP_REAL_COST_REDUCTION = 0.025  # -2.5%/year real, from_year=2027
ASHP_SUBSIDY_SCENARIO = "fast stepdown"
ASHP_MAINTENANCE_COST_PER_VISIT = 100.0
ASHP_MAINTENANCE_FREQUENCY = 1.0

ASHP_HEAT_DEMAND_UPLIFT = 0.08  # Adjusts ASHP heat demand relative to gas boiler heat demand
# ASHPs run at lower flow temperatures for longer, which can increase overall heat demand
# relative to a gas boiler in the same property. Set to 0 to assume no difference in demand
# between the two systems. Source: https://www.sciencedirect.com/science/article/pii/S037877882100061X

ASHP_INTEREST_RATE = 0.05
ASHP_LOAN_TERM = 15

ASHP_ELECTRICITY_TOU_TARIFF_DISCOUNT = 0.15  # 15% saving on unit rate, assumed for ASHP owners on a ToU tariff

BOILER_EFFICIENCY = 0.85
BOILER_LIFESPAN = 15
BOILER_INSTALLATION_COST_2026 = 3_000  # £, 2026 real, flat (0% real change)
BOILER_MAINTENANCE_COST_PER_VISIT = 80.0
BOILER_MAINTENANCE_FREQUENCY = 1.0

INSTALLATION_YEARS = range(config["install_start_year"], config["install_end_year"] + 1)

# ---------------------------------------------------------------------------
# Setting 'typical' household parameters
# These are subject to change until we settle on our definition and approach
# ---------------------------------------------------------------------------
ASHP_SPACE_HEAT_DEMAND = 13_690  # kWh/year
ASHP_DOMESTIC_HOT_WATER_HEAT_DEMAND = 3_150  # kWh/year
ASHP_INSTALLATION_COST_2026 = 12_310  # £, 2026 real

PROPERTY_DESCRIPTION = "6-7 habitable rooms (3-4 bedrooms), (semi-)detached house"


# ---------------------------------------------------------------------------
# 1. Load data
# ---------------------------------------------------------------------------
def load_ashp_subsidy_trajectory(scenario: str) -> SubsidyTrajectory:
    """Build a real-terms SubsidyTrajectory for ASHP from the named scenario in the subsidy options table."""
    subsidy_df = data_getters.get_ashp_subsidy_options_data()
    scenario_row = subsidy_df[subsidy_df["model"] == scenario].drop(columns="model").iloc[0]
    scenario_values = {int(year): value for year, value in scenario_row.items() if int(year) in INSTALLATION_YEARS}

    trajectory = SubsidyTrajectory("air_to_water_heat_pump", starting_subsidy=scenario_values[BASE_YEAR])
    trajectory.set_trajectory(scenario_values)
    trajectory.to_real(base_year=BASE_YEAR, inflation_rate=INFLATION_RATE)
    return trajectory


def load_gas_boiler_subsidy_trajectory() -> SubsidyTrajectory:
    """Build a flat, zero-value real-terms SubsidyTrajectory for gas boilers (no subsidy scheme)."""
    return SubsidyTrajectory("gas_boiler", starting_subsidy=0.0, price_basis="real", base_year=BASE_YEAR)


def load_latest_energy_price_trajectory(fuel: str) -> EnergyPriceTrajectory:
    """Build a flat, real-terms EnergyPriceTrajectory seeded from the latest price cap rate."""
    latest_price = data_getters.get_latest_price_cap_rate(fuel)  # p/kWh
    return EnergyPriceTrajectory(fuel, starting_price=latest_price, price_basis="real", base_year=BASE_YEAR)


def load_latest_gas_standing_charge() -> float:
    """Fetch latest gas standing charge from Ofgem price cap data."""
    return data_getters.get_latest_price_cap_standing_charge(fuel="gas")


# ---------------------------------------------------------------------------
# 2. Build trajectories
# ---------------------------------------------------------------------------
ashp_installation_costs = InstallationCostTrajectory(
    "air_to_water_heat_pump", starting_cost=ASHP_INSTALLATION_COST_2026, price_basis="real", base_year=BASE_YEAR
)
ashp_installation_costs.set_trajectory(-ASHP_REAL_COST_REDUCTION, from_year=BASE_YEAR + 1)

ashp_subsidies = load_ashp_subsidy_trajectory(ASHP_SUBSIDY_SCENARIO)
ashp_subsidies_zero = SubsidyTrajectory(
    "air_to_water_heat_pump", starting_subsidy=0.0, price_basis="real", base_year=BASE_YEAR
)

boiler_installation_costs = InstallationCostTrajectory(
    "gas_boiler", starting_cost=BOILER_INSTALLATION_COST_2026, price_basis="real", base_year=BASE_YEAR
)
# flat in real terms so no set_trajectory call needed

boiler_subsidies = load_gas_boiler_subsidy_trajectory()

electricity_prices = load_latest_energy_price_trajectory("electricity")  # flat at current
gas_prices = load_latest_energy_price_trajectory("gas")  # flat at current

ashp_electricity_prices = EnergyPriceTrajectory(
    "electricity",
    starting_price=electricity_prices.get_price(year=BASE_YEAR),
    price_basis="real",
    base_year=BASE_YEAR,
)
ashp_electricity_prices.prices = electricity_prices.prices.copy()
ashp_electricity_prices.apply_percentage_discount(ASHP_ELECTRICITY_TOU_TARIFF_DISCOUNT)

ashp_heat_demand = ASHP_SPACE_HEAT_DEMAND + ASHP_DOMESTIC_HOT_WATER_HEAT_DEMAND  # already includes ASHP uplift
boiler_heat_demand = ashp_heat_demand / (1 + ASHP_HEAT_DEMAND_UPLIFT)  # baseline demand, uplift removed

gas_standing_charge = load_latest_gas_standing_charge()


# ---------------------------------------------------------------------------
# 3. Build HeatingSystem for each installation year
# ---------------------------------------------------------------------------
def build_systems_for_year(
    installation_year: int,
) -> tuple[HeatingSystem, HeatingSystem, HeatingSystem, HeatingSystem]:
    """Build ASHP, ASHP (financed), ASHP (no subsidy), and gas boiler HeatingSystem objects for a given installation year."""
    heat_pump = HeatingSystem(
        system_type="air_to_water_heat_pump",
        installation_year=installation_year,
        lifespan=ASHP_LIFESPAN,
        efficiency=ASHP_EFFICIENCY,
        installation_cost_trajectory=ashp_installation_costs,
        subsidy_trajectory=ashp_subsidies,
        maintenance_cost_per_visit=ASHP_MAINTENANCE_COST_PER_VISIT,
        maintenance_annual_frequency=ASHP_MAINTENANCE_FREQUENCY,
    )
    heat_pump_financed = HeatingSystem(
        system_type="air_to_water_heat_pump",
        installation_year=installation_year,
        lifespan=ASHP_LIFESPAN,
        efficiency=ASHP_EFFICIENCY,
        installation_cost_trajectory=ashp_installation_costs,
        subsidy_trajectory=ashp_subsidies,
        maintenance_cost_per_visit=ASHP_MAINTENANCE_COST_PER_VISIT,
        maintenance_annual_frequency=ASHP_MAINTENANCE_FREQUENCY,
        interest_rate=ASHP_INTEREST_RATE,
        loan_term=ASHP_LOAN_TERM,
    )
    heat_pump_no_subsidy = HeatingSystem(
        system_type="air_to_water_heat_pump",
        installation_year=installation_year,
        lifespan=ASHP_LIFESPAN,
        efficiency=ASHP_EFFICIENCY,
        installation_cost_trajectory=ashp_installation_costs,
        subsidy_trajectory=ashp_subsidies_zero,
        maintenance_cost_per_visit=ASHP_MAINTENANCE_COST_PER_VISIT,
        maintenance_annual_frequency=ASHP_MAINTENANCE_FREQUENCY,
    )
    gas_boiler = HeatingSystem(
        system_type="gas_boiler",
        installation_year=installation_year,
        lifespan=BOILER_LIFESPAN,
        efficiency=BOILER_EFFICIENCY,
        installation_cost_trajectory=boiler_installation_costs,
        subsidy_trajectory=boiler_subsidies,
        maintenance_cost_per_visit=BOILER_MAINTENANCE_COST_PER_VISIT,
        maintenance_annual_frequency=BOILER_MAINTENANCE_FREQUENCY,
    )

    return heat_pump, heat_pump_financed, heat_pump_no_subsidy, gas_boiler


# ---------------------------------------------------------------------------
# 4a. Comparison tab of cost breakdown
# ---------------------------------------------------------------------------
def build_comparison_rows(installation_year: int) -> list[dict]:
    """Build tidy rows: one row per (installation_year, system, metric)."""
    heat_pump, heat_pump_financed, heat_pump_no_subsidy, gas_boiler = build_systems_for_year(
        installation_year=installation_year
    )

    systems = {
        "Heat pump": (heat_pump, ashp_heat_demand, ashp_electricity_prices, {}),
        "Heat pump (financed)": (heat_pump_financed, ashp_heat_demand, ashp_electricity_prices, {}),
        "Heat pump (no subsidy)": (heat_pump_no_subsidy, ashp_heat_demand, ashp_electricity_prices, {}),
        "Gas boiler": (gas_boiler, boiler_heat_demand, gas_prices, {}),
        "Gas boiler (incl. gas standing charge)": (
            gas_boiler,
            boiler_heat_demand,
            gas_prices,
            {"standing_charge": gas_standing_charge},
        ),
    }

    rows = []
    for system_name, (system, heat_demand, energy_price_trajectory, extra_kwargs) in systems.items():
        metrics = {
            "Lifespan": system.lifespan,
            "Efficiency": system.efficiency,
            "Heat demand (kWh/year)": heat_demand,
            "Interest rate": system.interest_rate,
            "Loan term": system.loan_term,
            "Discounted capital cost": system.calculate_discounted_lifetime_capital_cost(discount_rate=DISCOUNT_RATE),
            "Discounted loan interest": (
                system.calculate_discounted_lifetime_loan_interest(discount_rate=DISCOUNT_RATE)
                if system.is_financed
                else 0.0
            ),
            "Discounted maintenance cost": system.calculate_discounted_lifetime_maintenance_cost(
                discount_rate=DISCOUNT_RATE
            ),
            "Discounted running cost": system.calculate_discounted_lifetime_running_cost(
                heat_demand=heat_demand,
                energy_price_trajectory=energy_price_trajectory,
                discount_rate=DISCOUNT_RATE,
                **extra_kwargs,
            ),
            "Total discounted lifetime cost": system.calculate_discounted_lifetime_cost(
                heat_demand=heat_demand,
                energy_price_trajectory=energy_price_trajectory,
                discount_rate=DISCOUNT_RATE,
                **extra_kwargs,
            ),
            "Annualised discounted lifetime cost (EAC)": system.calculate_annualised_discounted_lifetime_cost(
                heat_demand=heat_demand,
                energy_price_trajectory=energy_price_trajectory,
                discount_rate=DISCOUNT_RATE,
                **extra_kwargs,
            ),
            # EAC breakdown: same discounted components above, converted to a level annual figure
            "EAC: capital cost": system.calculate_annualised_discounted_lifetime_capital_cost(
                discount_rate=DISCOUNT_RATE
            ),
            "EAC: loan interest": (
                system.calculate_annualised_discounted_lifetime_loan_interest(discount_rate=DISCOUNT_RATE)
                if system.is_financed
                else 0.0
            ),
            "EAC: maintenance cost": system.calculate_annualised_discounted_lifetime_maintenance_cost(
                discount_rate=DISCOUNT_RATE
            ),
            "EAC: running cost": system.calculate_annualised_discounted_lifetime_running_cost(
                heat_demand=heat_demand,
                energy_price_trajectory=energy_price_trajectory,
                discount_rate=DISCOUNT_RATE,
                **extra_kwargs,
            ),
        }
        for metric_name, value in metrics.items():
            rows.append(
                {
                    "installation_year": installation_year,
                    "system": system_name,
                    "metric": metric_name,
                    "value": value,
                }
            )

    return rows


comparison_rows = [row for year in INSTALLATION_YEARS for row in build_comparison_rows(installation_year=year)]
comparison_df = pd.DataFrame(comparison_rows)


# ---------------------------------------------------------------------------
# 4b. Annual breakdown tab with discounted cost of ownership for each individual operating year
#
# All figures discounted to present value using discount_base_year=installation_year
# ---------------------------------------------------------------------------
def build_annual_breakdown_rows(installation_year: int) -> list[dict]:
    """Build tidy rows: one row per (installation_year, operating_year, system, metric)."""
    heat_pump, heat_pump_financed, heat_pump_no_subsidy, gas_boiler = build_systems_for_year(
        installation_year=installation_year
    )

    systems = {
        "Heat pump (no subsidy)": (heat_pump_no_subsidy, ashp_heat_demand, electricity_prices, {}),
        "Heat pump": (heat_pump, ashp_heat_demand, electricity_prices, {}),
        "Heat pump (financed)": (heat_pump_financed, ashp_heat_demand, electricity_prices, {}),
        "Gas boiler": (gas_boiler, boiler_heat_demand, gas_prices, {}),
        "Gas boiler (incl. gas standing charge)": (
            gas_boiler,
            boiler_heat_demand,
            gas_prices,
            {"standing_charge": gas_standing_charge},
        ),
    }

    rows = []
    for system_name, (system, heat_demand, energy_price_trajectory, extra_kwargs) in systems.items():
        for operating_year in system.operating_years:
            discounted_running_cost = system.calculate_discounted_running_cost(
                year=operating_year,
                heat_demand=heat_demand,
                energy_price_trajectory=energy_price_trajectory,
                discount_rate=DISCOUNT_RATE,
                **extra_kwargs,
            )
            discounted_maintenance_cost = system.calculate_discounted_maintenance_cost(
                year=operating_year, discount_rate=DISCOUNT_RATE
            )

            # Capital/financing cashflow, actually paid in THIS specific year:
            if system.is_financed:
                loan_end_year = system.installation_year + system.loan_term - 1
                if operating_year <= loan_end_year:
                    discounted_capital_cost = system.calculate_discounted_loan_repayment(
                        year=operating_year, discount_rate=DISCOUNT_RATE
                    )
                else:
                    discounted_capital_cost = 0.0  # loan already fully repaid by this year
            else:
                # unfinanced: the full upfront cost lands entirely in the installation year
                discounted_capital_cost = (
                    system.calculate_discounted_lifetime_capital_cost(discount_rate=DISCOUNT_RATE)
                    if operating_year == installation_year
                    else 0.0
                )

            metrics = {
                "Discounted running cost": discounted_running_cost,
                "Discounted maintenance cost": discounted_maintenance_cost,
                "Discounted capital cost": discounted_capital_cost,
                "Discounted annual cost": (
                    discounted_running_cost + discounted_maintenance_cost + discounted_capital_cost
                ),
            }
            for metric_name, value in metrics.items():
                rows.append(
                    {
                        "installation_year": installation_year,
                        "operating_year": operating_year,
                        "system": system_name,
                        "metric": metric_name,
                        "value": value,
                    }
                )

    return rows


annual_breakdown_rows = [
    row for year in INSTALLATION_YEARS for row in build_annual_breakdown_rows(installation_year=year)
]
annual_breakdown_df = pd.DataFrame(annual_breakdown_rows)

# ---------------------------------------------------------------------------
# 4c. Summary tab with equivalent annual cost for each system in each installation year
# ---------------------------------------------------------------------------
eac_summary_df = comparison_df[comparison_df["metric"] == "Annualised discounted lifetime cost (EAC)"].pivot(
    index="installation_year", columns="system", values="value"
)

# Order columns sensibly rather than relying on pivot's default alphabetical order
summary_system_order = [
    "Heat pump (no subsidy)",
    "Heat pump",
    "Heat pump (financed)",
    "Gas boiler",
    "Gas boiler (incl. gas standing charge)",
]
eac_summary_df = eac_summary_df[summary_system_order]

# Quick "which is cheapest" column, comparing the core options
core_comparison_systems = ["Heat pump", "Gas boiler"]
eac_summary_df["Cheapest option"] = eac_summary_df[core_comparison_systems].idxmin(axis=1)

eac_summary_df = eac_summary_df.round(0)
eac_summary_df.index.name = "Installation year"

# ---------------------------------------------------------------------------
# 5. Save out to Excel in separate tabs
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "outputs" / "reports"
OUTPUT_PATH = OUTPUT_DIR / "lifetime_cost_comparison.xlsx"

with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl") as writer:
    eac_summary_df.to_excel(writer, sheet_name="Summary", startrow=2)
    comparison_df.to_excel(writer, sheet_name="Comparison", index=False)
    annual_breakdown_df.to_excel(writer, sheet_name="Annual breakdown", index=False)

    summary_sheet = writer.sheets["Summary"]

    # --- Title and description above the table ---
    summary_sheet["A1"] = "Equivalent Annual Cost (EAC) by installation year and heating system"
    summary_sheet["A2"] = (
        f"Present value, {BASE_YEAR} real £, discounted at {DISCOUNT_RATE:.1%}. "
        "Each row compares systems installed in the same year (see 'Comparison' tab for full breakdown)."
    )

print(f"Results saved to {OUTPUT_PATH}")

# ---------------------------------------------------------------------------
# 6. Plot: EAC by installation year, for each heating system
# ---------------------------------------------------------------------------
eac_df = comparison_df[comparison_df["metric"] == "Annualised discounted lifetime cost (EAC)"]

eac_chart = (
    alt.Chart(eac_df)
    .mark_line(point=True)
    .encode(
        x=alt.X("installation_year:O", title="Installation year"),
        y=alt.Y("value:Q", title="Annualised discounted lifetime cost (£/year)"),
        color=alt.Color("system:N", title="System"),
        tooltip=["system", "installation_year", alt.Tooltip("value:Q", format=",.0f", title="EAC (£/year)")],
    )
    .properties(width=700, height=400, title="Equivalent Annual Cost (EAC) by installation year and heating system")
)

eac_chart.save(str(OUTPUT_DIR / "eac_by_installation_year.html"))
print(f"Plot saved to {OUTPUT_DIR / 'eac_by_installation_year.html'}")

# ---------------------------------------------------------------------------
# 7. Plot: EAC component breakdown by system, installation_year=2026,
# with a dashed box + annotation showing the subsidy's effect on the heat pump
# ---------------------------------------------------------------------------
breakdown_year = 2026

bar_systems = [
    "Heat pump (no subsidy)",
    "Heat pump",
    "Heat pump (financed)",
    "Gas boiler",
    "Gas boiler (incl. gas standing charge)",
]

eac_component_metrics = [
    "EAC: capital cost",
    "EAC: loan interest",
    "EAC: maintenance cost",
    "EAC: running cost",
]

breakdown_df = comparison_df[
    (comparison_df["installation_year"] == breakdown_year)
    & (comparison_df["system"].isin(bar_systems))
    & (comparison_df["metric"].isin(eac_component_metrics))
].copy()

# Split capital cost into principal + interest so the stack doesn't double-count
capital_df = breakdown_df[breakdown_df["metric"] == "EAC: capital cost"].set_index("system")["value"]
interest_df = breakdown_df[breakdown_df["metric"] == "EAC: loan interest"].set_index("system")["value"]
principal_only = (capital_df - interest_df).rename("value").reset_index()
principal_only["metric"] = "EAC: capital cost (principal)"

breakdown_df = breakdown_df[breakdown_df["metric"] != "EAC: capital cost"]
breakdown_df.loc[breakdown_df["metric"] == "EAC: loan interest", "metric"] = "EAC: capital cost (interest)"
breakdown_df = pd.concat([breakdown_df, principal_only], ignore_index=True)

component_order = [
    "EAC: capital cost (principal)",
    "EAC: capital cost (interest)",
    "EAC: maintenance cost",
    "EAC: running cost",
]

stacked_bar = (
    alt.Chart(breakdown_df)
    .mark_bar()
    .encode(
        x=alt.X("system:N", sort=bar_systems, title="Heating system", axis=alt.Axis(labelAngle=-20)),
        y=alt.Y("value:Q", stack="zero", title="Equivalent Annual Cost (£/year)"),
        color=alt.Color("metric:N", sort=component_order, title="Cost component"),
        order=alt.Order("metric:N", sort="ascending"),
        tooltip=["system", "metric", alt.Tooltip("value:Q", format=",.0f")],
    )
)

value_labels = (
    alt.Chart(breakdown_df)
    .mark_text(color="white", fontSize=10)
    .transform_stack(
        stack="value",
        groupby=["system"],
        sort=[{"field": "metric", "order": "ascending"}],
        as_=["stack_start", "stack_end"],
    )
    .transform_calculate(mid="(datum.stack_start + datum.stack_end) / 2")
    .transform_filter(alt.datum.value > 0)
    .encode(
        x=alt.X("system:N", sort=bar_systems),
        y=alt.Y("mid:Q", title=None),
        text=alt.Text("value:Q", format=",.0f"),
    )
)

# Subsidy saving annotation
heat_pump_eac = eac_df.query("installation_year == @breakdown_year and system == 'Heat pump'")["value"].iloc[0]
heat_pump_no_subsidy_eac = eac_df.query("installation_year == @breakdown_year and system == 'Heat pump (no subsidy)'")[
    "value"
].iloc[0]
subsidy_saving = heat_pump_no_subsidy_eac - heat_pump_eac

annotation_df = pd.DataFrame(
    {"system": ["Heat pump"], "y_bottom": [heat_pump_eac], "y_top": [heat_pump_no_subsidy_eac]}
)

subsidy_box = (
    alt.Chart(annotation_df)
    .mark_rect(fill=None, stroke="black", strokeDash=[4, 2])
    .encode(x=alt.X("system:N", sort=bar_systems), y="y_bottom:Q", y2="y_top:Q")
)

subsidy_label = (
    alt.Chart(annotation_df)
    .mark_text(align="left", dx=10, dy=-8, fontSize=11)
    .encode(
        x=alt.X("system:N", sort=bar_systems),
        y=alt.Y("y_top:Q"),
        text=alt.value(f"Subsidy saving: £{subsidy_saving:,.0f}/year"),
    )
)

full_chart = (stacked_bar + value_labels + subsidy_box + subsidy_label).properties(
    width=700,
    height=450,
    title=f"Equivalent Annual Cost component breakdown (Present value annual cost, 2026 £/year real terms), installation year {breakdown_year}",
)

full_chart.save(str(OUTPUT_DIR / f"eac_breakdown_with_subsidy_effect_{breakdown_year}.html"))
print(f"Plot saved to {OUTPUT_DIR / f'eac_breakdown_with_subsidy_effect_{breakdown_year}.html'}")

# ---------------------------------------------------------------------------
# 8. Plot: cashflow by year of ownership, installation_year=2026
# ---------------------------------------------------------------------------
cashflow_df = annual_breakdown_df[annual_breakdown_df["installation_year"] == 2026].copy()
cashflow_df["year_of_ownership"] = cashflow_df["operating_year"] - cashflow_df["installation_year"]

systems_to_show = [
    "Heat pump (no subsidy)",
    "Heat pump",
    "Heat pump (financed)",
    "Gas boiler",
    "Gas boiler (incl. gas standing charge)",
]
cashflow_df = cashflow_df[cashflow_df["system"].isin(systems_to_show)]

# --- Year 0: stacked bar, one bar per system, broken down by component ---
year0_component_metrics = ["Discounted capital cost", "Discounted maintenance cost", "Discounted running cost"]
year0_df = cashflow_df[(cashflow_df["year_of_ownership"] == 0) & (cashflow_df["metric"].isin(year0_component_metrics))]

year0_bar = (
    alt.Chart(year0_df)
    .mark_bar()
    .encode(
        x=alt.X("system:N", sort=systems_to_show, title=None, axis=alt.Axis(labelAngle=-40)),
        y=alt.Y("value:Q", stack="zero", title="Present value cost, 2026 £ (real terms)"),
        color=alt.Color(
            "metric:N",
            sort=year0_component_metrics,
            title="Cost component",
            scale=alt.Scale(domain=year0_component_metrics, range=["#1f77b4", "#2ca02c", "#d62728"]),
        ),
        order=alt.Order("metric:N", sort="ascending"),
        tooltip=["system", "metric", alt.Tooltip("value:Q", format=",.0f")],
    )
)

year0_labels = (
    alt.Chart(year0_df)
    .mark_text(color="white", fontSize=9)
    .transform_stack(
        stack="value",
        groupby=["system"],
        sort=[{"field": "metric", "order": "ascending"}],
        as_=["stack_start", "stack_end"],
    )
    .transform_calculate(mid="(datum.stack_start + datum.stack_end) / 2")
    .transform_filter(alt.datum.value > 0)
    .encode(
        x=alt.X("system:N", sort=systems_to_show),
        y=alt.Y("mid:Q", title=None),
        text=alt.Text("value:Q", format=",.0f"),
    )
)

year0_chart = (year0_bar + year0_labels).properties(
    width=280, height=450, title=["Year 0: installation", "(capex + first year of operation, present value 2026 £)"]
)

# --- Years 1-14: subsequent years of operation ---
opex_df = cashflow_df[(cashflow_df["year_of_ownership"] > 0) & (cashflow_df["metric"] == "Discounted annual cost")]

opex_chart = (
    alt.Chart(opex_df)
    .mark_line(point=True)
    .encode(
        x=alt.X("year_of_ownership:O", title="Year of ownership"),
        y=alt.Y("value:Q", title="Present value annual cost, 2026 £/year (real terms)"),
        color=alt.Color("system:N", sort=systems_to_show, title="System"),
        tooltip=["system", "year_of_ownership", alt.Tooltip("value:Q", format=",.0f")],
    )
    .properties(
        width=700,
        height=450,
        title=[
            "Years 1-14: subsequent years of operation",
            "(running + maintenance, plus loan repayments if financed)",
        ],
    )
)

cashflow_chart = alt.hconcat(year0_chart, opex_chart).resolve_scale(color="independent")

# --- Price ratio table, as two labeled text-mark rows beneath the cashflow charts ---
years_shown = [2026 + y for y in sorted(cashflow_df["year_of_ownership"].unique())]

price_ratio_df = pd.concat(
    [
        pd.DataFrame(
            {
                "year": years_shown,
                "rate_type": "Price cap electricity rate",
                "ratio": [
                    electricity_prices.get_price(year=year) / gas_prices.get_price(year=year) for year in years_shown
                ],
            }
        ),
        pd.DataFrame(
            {
                "year": years_shown,
                "rate_type": "ASHP effective electricity rate",
                "ratio": [
                    ashp_electricity_prices.get_price(year=year) / gas_prices.get_price(year=year)
                    for year in years_shown
                ],
            }
        ),
    ],
    ignore_index=True,
)

price_ratio_chart = (
    alt.Chart(price_ratio_df)
    .mark_text(fontSize=11)
    .encode(
        x=alt.X("year:O", title=None),
        y=alt.Y("rate_type:N", title=None, axis=alt.Axis(labelLimit=200)),
        text=alt.Text("ratio:Q", format=".2f"),
    )
    .properties(width=980, height=80, title="Electricity/gas price ratio by year")
)

full_cashflow_chart = alt.vconcat(cashflow_chart, price_ratio_chart)
full_cashflow_chart.save(str(OUTPUT_DIR / "cashflow_by_year_of_ownership_2026.html"))
print(f"Plot saved to {OUTPUT_DIR / 'cashflow_by_year_of_ownership_2026.html'}")
