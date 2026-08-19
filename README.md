# ASF Lifetime Cost Model

An analytical model that estimates the lifetime cost of heating systems under differing assumptions for upfront costs, running costs, subsidies and financing.

Given a set of assumptions (energy prices, installation costs, subsidies, efficiency, financing terms, etc.), the model calculates and compares, for a heating system:

- **Running cost** - cost of energy consumed over the system's lifespan
- **Maintenance cost** - servicing costs
- **Capital cost** - upfront installation cost (net of any subsidy), or loan repayments if financed
- **Lifetime cost** - the sum of the above, available undiscounted, discounted to present value, or annualised as an Equivalent Annual Cost (EAC) for comparing systems with different cost timing profiles or lifespans

## Related projects

This model is also used as the calculation backend for [`asf_lifetime_cost_app`](https://github.com/nestauk/asf_lifetime_cost_app), a Streamlit front end that provides an interactive UI for comparisons between heat pumps and gas boilers.

## Repo structure

```
asf_lifetime_cost_model/
├── models/          # Core model classes (trajectories, HeatingSystem, cost calculations)
├── getters/         # Data access, e.g. fetching current energy price cap rates
├── analysis/
│   ├── notebooks/   # Jupyter notebook analysis scripts and demos
│   └── reviews/     # Supporting evidence review
├── config/          # Default modelling assumptions (base.yaml) and logging config
└── utils/           # Shared helper functions
outputs/             # Generated figures and reports
```

## Setup

### Prerequisites

- Python 3.11+ (uv will install this automatically if needed)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for dependency management

This project uses [`uv`](https://docs.astral.sh/uv/) for virtual environment management. If you are new to `uv`, you can find the [quickstart guide here](https://docs.astral.sh/uv/getting-started/).

### Installation

```bash
# Clone the repo
git clone https://github.com/nestauk/asf_lifetime_cost_model.git
cd asf_lifetime_cost_model

# Install dependencies (creates .venv automatically)
uv sync

# Activate virtual environment
source .venv/bin/activate
```

## Usage

The core model classes (`EnergyPriceTrajectory`, `InstallationCostTrajectory`,
`SubsidyTrajectory`, `HeatingSystem`) live in `asf_lifetime_cost_model/models/`
and can be imported directly, e.g.:

```python
from asf_lifetime_cost_model.models.trajectory import EnergyPriceTrajectory
from asf_lifetime_cost_model.models.heating_system import HeatingSystem
```

For a walkthrough of
how the model classes fit together, see
[`asf_lifetime_cost_model/analysis/notebooks/model_architecture_demo.py`](asf_lifetime_cost_model/analysis/notebooks/model_architecture_demo.py)
(Open it as a Jupyter notebook). For an explanation of the full architecture, available
cost calculation methods, and config-driven defaults, see
[`asf_lifetime_cost_model/models/README.md`](asf_lifetime_cost_model/models/README.md).

---

<small>Last updated: 19 August 2026 by Elysia Lucas</small>
