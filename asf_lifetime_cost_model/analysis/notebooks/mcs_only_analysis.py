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

# %% [markdown]
# ## Identifying average heat demand and install cost for a 'typical' household installing an ASHP

# %%
import datetime

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# %% [markdown]
# ### MCS installations data only

# %%
mcs_df = pd.read_csv(
    "s3://asf-core-data/inputs/MCS/latest_raw_data/historical/raw_historical_mcs_installations_20260705.csv"
)

# %%
# Change commission date format to datetime type
mcs_df["Commissioning Date"] = pd.to_datetime(mcs_df["Commissioning Date"], format="%d/%m/%Y", errors="coerce")

# %%
# Filter for installs in timeline and types of interest
# FY2025/26
df = mcs_df[
    (mcs_df["Technology Type"] == "Air Source Heat Pump")
    & (mcs_df["Installation Type"] == "Domestic")
    & (mcs_df["Project Type"] == "Retrofit")
    & (
        ((mcs_df["Commissioning Date"].dt.year == 2025) & (mcs_df["Commissioning Date"].dt.quarter.isin([2, 3, 4])))
        | ((mcs_df["Commissioning Date"].dt.year == 2026) & (mcs_df["Commissioning Date"].dt.quarter == 1))
    )
    & (mcs_df["Renewable System Design"] == "Space heat and DHW")
].copy()

# %%
# Drop duplicate rows
df = df.drop_duplicates()

# %%
# Add a new column counting number of heat pump/units included in the installation
dupe_mask = df["InstallationID"].duplicated(keep=False)
multi_unit_sales = df[dupe_mask]
unit_counts = df.groupby("InstallationID").size().reset_index(name="n_units")
multi_unit_ids = unit_counts[unit_counts["n_units"] > 1]
df["n_units"] = df.groupby("InstallationID")["InstallationID"].transform("size")

# df.loc[df["n_units"] > 1]

# %%
# Note: installations for very high heat demand/generation need multiple units
df.loc[df["n_units"] > 1, "Total Installed Capacity"].agg(["min", "median", "max"])

# %%
# Add a total heat demand column
df["annual_total_heating_demand"] = df["Annual Space Heating Demand"] + df["Annual Water Heating Demand"]

# %%
# Note: installations for very high heat demand/generation need multiple units
df.loc[df["n_units"] > 1, "annual_total_heating_demand"].agg(["min", "median", "max"])

# %%
# Clean outliers
df = df[df["annual_total_heating_demand"] <= 100_000]

# %% [markdown]
# Overall statistics

# %%
# Number of installations (unique IDs)
print(f"Number of domestic, retrofit ASHP installations in FY 2025/26: {df['InstallationID'].nunique():,.0f}")

# %%
median_capacity = df.drop_duplicates(subset="InstallationID")["Total Installed Capacity"].median()
print(f"Median installed capacity of domestic, retrofit ASHP installations in 2025/26: {median_capacity:,.0f} kW")

# %%
median_cost = df.drop_duplicates(subset="InstallationID")["Overall Cost"].median()
print(f"Median cost of domestic, retrofit ASHP installations in 2025/26: £{median_cost:,.0f}")

# %%
median_heat_demand = df.drop_duplicates(subset="InstallationID")["annual_total_heating_demand"].median()
print(
    f"Median annual heating demand of domestic, retrofit ASHP installations in 2025/26: {median_heat_demand:,.0f} kWh/yr"
)

# %% [markdown]
# ---

# %% [markdown]
# Exploratory: Grouping into capacity bands

# %%
# Group capacity into bins
bins = [0, 4, 6, 8, 10, 12, 14, 16, 18, 20, float("inf")]
labels = [
    "0kW to 4kW",
    "4kW to 6kW",
    "6kW to 8kW",
    "8kW to 10kW",
    "10kW to 12kW",
    "12kW to 14kW",
    "14kW to 16kW",
    "16kW to 18kW",
    "18kW to 20kW",
    "Greater than 20kW",
]

df["capacity_band"] = pd.cut(df["Total Installed Capacity"], bins=bins, labels=labels, right=False)

pct_breakdown = df["capacity_band"].value_counts(normalize=True).reindex(labels) * 100
print(pct_breakdown.round(1))

# %%
capacity_check = df.groupby("InstallationID")["capacity_band"].nunique()
print(capacity_check[capacity_check > 1])  # should be empty if capacity_band is truly install level

# %%
capacity_band_counts = df.drop_duplicates(subset="InstallationID")["capacity_band"].value_counts().sort_index()

pct_breakdown = (capacity_band_counts / capacity_band_counts.sum()) * 100
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(pct_breakdown.index, pct_breakdown.values, color="#4C72B0", edgecolor="white")

ax.set_ylabel("% of installations")
ax.set_xlabel("Capacity band (kW)")
ax.set_title("Distribution of capacity of ASHPs installed (FY 2025/26)")
plt.xticks(rotation=40, ha="right")

# % labels on top of each bar
for bar in bars:
    height = bar.get_height()
    if height > 0:
        ax.annotate(
            f"{height:.1f}%",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            fontsize=9,
        )

plt.tight_layout()
plt.show()

# %% [markdown]
# Most common (mode) capacity band for installations in FY 2025/26 is 8-10 kW

# %%
df[["Overall Cost", "Total Installed Capacity"]].corr()

# %%
df["annual_total_heating_demand"].describe()

# %%
plot_df = df.drop_duplicates(subset="InstallationID")

fig, ax = plt.subplots(figsize=(10, 6))

sns.kdeplot(data=plot_df, x="annual_total_heating_demand", hue="capacity_band", common_norm=False, fill=False, ax=ax)

# Add a vertical line for each band's median
palette = sns.color_palette(n_colors=plot_df["capacity_band"].nunique())
for color, (band, group) in zip(palette, plot_df.groupby("capacity_band")):
    median_val = group["annual_total_heating_demand"].median()
    ax.axvline(median_val, color=color, linestyle="--", linewidth=1, alpha=0.7)

ax.set_xlabel("Heat demand (kWh/yr)")
ax.set_ylabel("Density")
ax.set_title("Heat demand distribution by capacity band (dashed = median)")

plt.tight_layout()
plt.show()

# %% [markdown]
# ---

# %% [markdown]
# 8 to 10 kW (most common capacity band)

# %%
band_subset = df[df["capacity_band"] == "8kW to 10kW"]

# %%
# remove outliers
q1 = band_subset["Overall Cost"].quantile(0.25)
q3 = band_subset["Overall Cost"].quantile(0.75)
iqr = q3 - q1
lower = q1 - 1.5 * iqr
upper = q3 + 1.5 * iqr

band_clean = band_subset[(band_subset["Overall Cost"] >= lower) & (band_subset["Overall Cost"] <= upper)]

# %%
fig, ax = plt.subplots(figsize=(6, 6))
ax.boxplot(band_subset["Overall Cost"].dropna(), vert=True)

ax.set_ylabel("Installed cost (£)")
ax.set_title("Cost distribution for 8kW to 10kW band (n={})".format(len(band_subset)))
ax.set_xticklabels(["8kW to 10kW"])

# IQR bounds
ax.axhline(lower, color="firebrick", linestyle="--", linewidth=1, label=f"Lower bound (£{lower:,.0f})")
ax.axhline(upper, color="firebrick", linestyle="--", linewidth=1, label=f"Upper bound (£{upper:,.0f})")
ax.legend(fontsize=8)

plt.tight_layout()

plt.show()

# %%
print("\n--- 8kW to 10kW (FY 2025/26) ---")
print(f"n = {len(band_clean)}")

# Numerical fields
print("\n--- Cost ---")
print(band_clean["Overall Cost"].describe())

print("\n--- Space heat demand ---")
print(band_clean["Annual Space Heating Demand"].describe())

print("\n--- DHW heat demand ---")
print(band_clean["Annual Water Heating Demand"].describe())

print("\n--- SCOP ---")
print(band_clean["SCOP"].describe())

# %%
