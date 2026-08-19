# ASF Lifetime Cost Model Architecture Overview

This document explains how the core model classes relate to each other:
`EnergyPriceTrajectory`, `InstallationCostTrajectory`, `SubsidyTrajectory`,
and `HeatingSystem`.

## Relationship diagram

```
EnergyPriceTrajectory          InstallationCostTrajectory        SubsidyTrajectory
(fuel, prices £/kWh)           (system_type, cost £)             (system_type, subsidy £)
2026-2050                      2026-2035                         2026-2035
        |                              |                                 |
        |  get_price(year),            |  get_cost(installation_year)    |  get_subsidy(installation_year)
        |  per operating_year          |                                 |
        v                              v                                 v
        +------------------------------+---------------------------------+
                                        |
                                        v
                              +----------------------+
                              |  HeatingSystem       |
                              |----------------------|
                              | system_type          |
                              | installation_year    |
                              | lifespan             |
                              | efficiency           |
                              | subsidy*             |
                              | installation_cost*   |
                              | maintenance          |
                              | financing (optional) |
                              +----------------------+
                                        |
                                        v
                        +----------------------------------+
                        |     Cost calculations            |
                        |----------------------------------|
                        | running / maintenance / capital  |
                        | lifetime / discounted / EAC**    |
                        +----------------------------------+
                                        |
                                        v
                        +----------------------------------+
                        |  Comparison calculations         |
                        |----------------------------------|
                        | build HeatingSystem instances    |
                        | for heat pump vs. gas boiler     |
                        +----------------------------------+

* looked up once from `InstallationCostTrajectory`/`SubsidyTrajectory` at
construction time, for the system's `installation_year` — not stored as a
trajectory, just a single fixed value from that point onward.
** EAC: Equivalent Annual Cost (£)
```

## How the pieces fit together

**Trajectories hold raw year-indexed data.**

`EnergyPriceTrajectory`,
`InstallationCostTrajectory`, and `SubsidyTrajectory` are independent,
interchangeable data containers. Each just holds a series of values
indexed by year, plus metadata (`fuel` or `system_type`, `price_basis`,
`base_year`). None of them know about `HeatingSystem` or each other.

**`HeatingSystem` is built once per installation year, and looks up its own inputs from the trajectories.** At construction, it calls
`installation_cost_trajectory.get_cost(installation_year)` and
`subsidy_trajectory.get_subsidy(installation_year)` once, to look up the installation cost and subsidy value for that installation year, and determines its
`upfront_cost`.

**`EnergyPriceTrajectory` is _not_ read at construction.** The logic behind this is that the tariff is not technically a set characteristic of the heating system, but is something that the owner can change. `EnergyPriceTrajectory` is fed into `HeatingSystem` by passing into explicit cost calculation methods later (`calculate_running_cost`,
`calculate_lifetime_cost`, etc.). Energy prices (and, therefore, running costs) vary year to year across the system's `operating_years`.

**Validation in** `HeatingSystem`
checks that every trajectory passed in:

- matches its own `system_type`/`fuel`,
- is in real terms (`price_basis="real"`),
- shares the same `base_year`,
- covers the full range of `operating_years`.

This exists because mixing nominal and real trajectories, or trajectories
anchored to different base years, would silently produce a wrong answer
rather than an error.

**`HeatingSystem` exposes layered cost calculations:**

| Level                                      | Undiscounted                          | Discounted (present value)                       | Annualised (EAC)                                            |
| ------------------------------------------ | ------------------------------------- | ------------------------------------------------ | ----------------------------------------------------------- |
| Running cost                               | `calculate_lifetime_running_cost`     | `calculate_discounted_lifetime_running_cost`     | `calculate_annualised_discounted_lifetime_running_cost`     |
| Maintenance cost                           | `calculate_lifetime_maintenance_cost` | `calculate_discounted_lifetime_maintenance_cost` | `calculate_annualised_discounted_lifetime_maintenance_cost` |
| Capital cost (+ loan interest if financed) | `calculate_lifetime_capital_cost`     | `calculate_discounted_lifetime_capital_cost`     | `calculate_annualised_discounted_lifetime_capital_cost`     |
| **Total**                                  | `calculate_lifetime_cost`             | `calculate_discounted_lifetime_cost`             | `calculate_annualised_discounted_lifetime_cost`             |

Each "Total" method is built by summing its three components, so the
components and the total are always internally consistent. You can fetch any single component's number and know it will sum correctly with the
others.

**Comparison analysis is not part of the model.**
The model itself has no concept of "comparison", so that logic lives entirely in the
analysis layer. See an example of how `HeatingSystem` objects are compared for analysis
in the demo notebook: [`model_architecture_demo.py`](../analysis/notebooks/model_architecture_demo.py)

## Config and default values

Several defaults used throughout the model come from `asf_lifetime_cost_model/config.py`
(loaded from `config/base.yaml`), rather than being hardcoded in the model classes:

| Config key                                    | Used for                                                                                   | Current default                                          |
| --------------------------------------------- | ------------------------------------------------------------------------------------------ | -------------------------------------------------------- |
| `operating_start_year` / `operating_end_year` | `EnergyPriceTrajectory`'s valid year range                                                 | 2026-2050                                                |
| `install_start_year` / `install_end_year`     | `InstallationCostTrajectory` / `SubsidyTrajectory`'s valid year range                      | 2026-2035                                                |
| `currency_unit`                               | Display unit for cost trajectories                                                         | `£`                                                      |
| `energy_price_unit`                           | Display unit for energy price trajectories                                                 | `p/kWh`                                                  |
| `fuel_by_system_type`                         | Maps `system_type` → `fuel` in `HeatingSystem`                                             | `air_to_water_heat_pump: electricity`, `gas_boiler: gas` |
| `default_discount_rate`                       | Default `discount_rate` for every `calculate_discounted_*`/`calculate_annualised_*` method | 0.035 (HMT Green Book)                                   |
| `default_inflation_rate`                      | Default `inflation_rate` for converting nominal trajectories to real via `.to_real()`      | 0.02                                                     |

Any of these can be overridden per call (e.g. passing `discount_rate=0.05` to
`calculate_discounted_lifetime_cost`) without touching `config.py`. The config
value is only used when not explicitly specified.

## Modelling quirks to remember

- All trajectories must be in **real terms** (`price_basis="real"`) and
  share one **`base_year`** before being used in a `HeatingSystem`.
- `discount_base_year` (used in every discounted/annualised method) is a
  **separate** concept from a trajectory's `base_year`. `discount_base_year` is the
  reference point for time-preference discounting, not inflation
  adjustment. Leave it as the default (`installation_year`) when comparing
  systems installed in the _same_ year; set it to a shared fixed year
  (e.g. 2026) when comparing systems installed in _different_ years.
- `operating_years` is fixed at construction as
  `range(installation_year, installation_year + lifespan)`. The
  installation year is also the system's first year of operation.

## Cost concepts explained

### Real vs. nominal

**Nominal** means the actual cash figure at the time, i.e, what you'd
see on a receipt or bill in a given year. **Real** means that same figure
adjusted to strip out inflation, expressed in a fixed base year's
purchasing power, so amounts from different years become genuinely
comparable.

A price that's _flat in nominal terms_ (e.g. £3,000 every year) is
actually _falling in real terms_, since inflation erodes what a fixed cash
amount can buy each year. Conversely, a price _flat in real terms_ means
its nominal (cash) value is rising each year, exactly in step with
inflation.

Every trajectory (`EnergyPriceTrajectory`, `InstallationCostTrajectory`,
`SubsidyTrajectory`) tracks its own `price_basis` ("nominal" or "real")
and `base_year`, and must be converted to real terms (via `.to_real()`)
before being used in a `HeatingSystem`. Mixing nominal and real
cashflows in the same calculation would silently produce a wrong answer.

### Undiscounted vs. discounted (present value)

**Undiscounted** costs are just added up at face value. A pound spent in
2026 and a pound spent in 2040 are treated as worth exactly the same.

**Discounted** (present value) costs account for the time value of money:
a pound spent in the future is worth less today than a pound spent now,
because money available today could otherwise be invested, and because
people generally prefer consumption sooner rather than later. Each year's
cost is multiplied by a discount factor, `1 / (1 + discount_rate) ** (year - discount_base_year)`, before summing. Costs further in the future
count for progressively less.

`discount_base_year` is the reference point discounting is measured
_from_. This is separate from a trajectory's `base_year` (which strips out
inflation). Leaving `discount_base_year` as the default
(`installation_year`) is correct when comparing systems installed in the
_same_ year. Comparing systems installed in _different_ years requires
passing a single shared `discount_base_year` (e.g. 2026) to every
calculation, so every system's costs are expressed in the same year's
present-value terms.

### Annualised lifetime cost vs. Equivalent Annual Cost (EAC)

**Annualised lifetime cost** (`calculate_annualised_lifetime_cost`) simply
divides the undiscounted lifetime total by the number of operating years. It's a simple average that ignores _when_ within the lifespan each cost
actually landed.

**Equivalent Annual Cost (EAC)**
(`calculate_annualised_discounted_lifetime_cost`) is the financially
correct version: it takes the _discounted_ lifetime cost (present value)
and converts it into a single, level annual payment whose present value
equals that same total. It uses the annuity-due formula, `EAC = NPV * r / ((1 + r) * (1 - (1 + r) ** -n))` — matching this model's discounting convention, where the first operating year is undiscounted. This is a close variant of the formula used to work out constant mortgage repayments from a loan amount.

EAC is the right metric for comparing heating systems, because it
correctly accounts for the fact that a heat pump (large upfront cost, low
running cost) and a gas boiler (small upfront cost, higher running cost)
have very different cost timing profiles. Simple annualisation would
under-value the true cost of upfront-heavy options. EAC is also the
correct way to compare systems with _different_ lifespans, since it
implicitly assumes each option is replaced identically forever, putting
both options on the same "cost per year" footing regardless of how long
each one lasts.

### Financing mechanisms

A `HeatingSystem` can be either:

- **Unfinanced** (`interest_rate=None`, `loan_term=None`): the full
  `upfront_cost` (installation cost minus subsidy) is paid as a single
  lump sum in the installation year.
- **Financed** (`interest_rate` and `loan_term` both provided): the loan
  is assumed to cover 100% of `upfront_cost` with **no deposit is modeled**.
  Repayments begin one year after installation (interest accrues from day
  one, but nothing is due until one full period has elapsed) and are
  spread evenly over `loan_term` years via the standard annuity formula. This
  means:
  - `calculate_annual_loan_repayment()`: the flat yearly repayment
    amount, which is _larger_ than `upfront_cost / loan_term`, since it
    includes interest on top of repaying the principal.
  - `calculate_lifetime_loan_interest()`: the total interest paid over
    the loan's life (total repayments minus the original principal).
  - `calculate_lifetime_capital_cost()`: for a financed system, this
    equals total repayments (principal + interest), not just the
    principal alone.

---

<small>Last updated: 04 August 2026 by Elysia Lucas</small>
