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
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from asf_lifetime_cost_model.getters.getter_utils import _read_s3_csv_to_dataframe

# %%
current_year = datetime.datetime.now().year

# %% [markdown]
# ### MCS installations data only

# %%
mcs_df = _read_s3_csv_to_dataframe(bucket_name="asf-core-data", s3_key="outputs/MCS/mcs_installations_260716.csv")

# %%
#  Ensure commission_date is in datetime format
mcs_df["commission_date"] = pd.to_datetime(mcs_df["commission_date"])

# %%
mcs_filtered_df = mcs_df[
    (mcs_df["tech_type"] == "Air Source Heat Pump")
    & (mcs_df["installation_type"] == "Domestic")
    & (mcs_df["Project Type"] == "Retrofit")
    & (mcs_df["commission_date"].dt.year == current_year)
    & (mcs_df["design"] == "Space heat and DHW")
].copy()

# %%
# Checking how many installs this year
len(mcs_filtered_df)

# %% [markdown]
# ### MCS and EPC joined data

# %%
mcs_epc_df = _read_s3_csv_to_dataframe(
    bucket_name="asf-core-data", s3_key="outputs/MCS/mcs_installations_epc_most_relevant_260716.csv"
)

# %%
mcs_epc_df.to_pickle("mcs_epc_df_temp.pkl")

# %% [markdown]
# Data fields of interest:
# - `commission_date`
# - `capacity`: Total installed capacity (kW)
# - `estimated_annual_generation`: Estimated energy produced in a year (kWh)
# - `scop`: Seasonal Coefficient of Performance
# - `heat_demand` and `water_demand` (Note: `capacity` = `heat_demand`): Annual space heating requirement (kWh/year), Annual water heating requirement (kWh/year)
# - `design` = `Space heat and DHW`
# - `cost`
# - `installation_type` = `Domestic`
# - `Project Type` = `Retrofit`
# - `tech_type` = `Air Source Heat Pump`
# - `NUMBER_HABITABLE_ROOMS`
# - `BUILT_FORM`
# - `PROPERTY_TYPE`
# - `MAINHEAT_DESCRIPTION` = `Boiler and radiators, mains gas`

# %%
#  Ensure commission_date is in datetime format
mcs_epc_df["commission_date"] = pd.to_datetime(mcs_epc_df["commission_date"])

# %%
# Filter for domestic ASHP in 2026 only
df = mcs_epc_df[
    (mcs_epc_df["tech_type"] == "Air Source Heat Pump")
    & (mcs_epc_df["installation_type"] == "Domestic")
    & (mcs_epc_df["Project Type"] == "Retrofit")
    & (mcs_epc_df["commission_date"].dt.year == current_year)
    & (mcs_epc_df["MAINHEAT_DESCRIPTION"] == "Boiler and radiators, mains gas")
    & (mcs_epc_df["design"] == "Space heat and DHW")
].copy()

# %%
# Looks like MM-DD are the wrong way round?
# df["commission_date"].unique()

# %% [markdown]
# Characterising installs by capacity bands used in BUS reporting
# - We're assuming that heat pumps are sized primarily based on property heat demand
# - Considering different capacity bands == different property heat demand levels == different property types

# %%
df[["heat_demand", "capacity"]].corr()

# %%
# add capacity bands
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

df["capacity_band"] = pd.cut(df["capacity"], bins=bins, labels=labels, right=False)

pct_breakdown = df["capacity_band"].value_counts(normalize=True).reindex(labels) * 100
print(pct_breakdown.round(1))

# %%
median_capacity = df["capacity"].median()

fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(pct_breakdown.index, pct_breakdown.values, color="#4C72B0", edgecolor="white")

ax.set_ylabel("% of installations")
ax.set_xlabel("Capacity band (kW)")
ax.set_title("Distribution of capacity of ASHPs installed in 2026")
plt.xticks(rotation=40, ha="right")

# Add % labels on top of each bar
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

# Mark the median capacity value
# Find which band the median falls into, to position the line at that bar's x-position
median_band_idx = pd.cut([median_capacity], bins=bins, labels=labels, right=False)[0]
band_position = labels.index(median_band_idx)

ax.axvline(band_position, color="firebrick", linestyle="--", linewidth=2)
ax.text(
    band_position,
    ax.get_ylim()[1] * 0.95,
    f" Median = {median_capacity:.1f} kW",
    color="firebrick",
    fontsize=10,
    va="top",
)

plt.tight_layout()

plt.show()

# %% [markdown]
# Heat demand distribution within each band

# %%
fig, ax = plt.subplots(figsize=(10, 6))

sns.kdeplot(data=df, x="heat_demand", hue="capacity_band", common_norm=False, fill=False, ax=ax)

# Add a vertical line for each band's median
palette = sns.color_palette(n_colors=df["capacity_band"].nunique())
for color, (band, group) in zip(palette, df.groupby("capacity_band")):
    median_val = group["heat_demand"].median()
    ax.axvline(median_val, color=color, linestyle="--", linewidth=1, alpha=0.7)

ax.set_xlabel("Heat demand (kWh/yr)")
ax.set_ylabel("Density")
ax.set_title("Heat demand distribution by capacity band (dashed = median)")

plt.tight_layout()
plt.show()

# %% [markdown]
# Cost distribution within each band

# %%
df[["cost", "capacity"]].corr()

# %%
fig, ax = plt.subplots(figsize=(10, 6))

sns.kdeplot(data=df, x="cost", hue="capacity_band", common_norm=False, fill=False, ax=ax)

ax.set_xlabel("Installation cost (£)")
ax.set_ylabel("Density")
ax.set_title("Installation cost by capacity band")

plt.tight_layout()
plt.show()

# %% [markdown]
# #### Per capacity band

# %% [markdown]
# 8 to 10 kW
# - Most common capacity band in BUS stats (2022/23, 2023/24, 2024/25, 2025/26)

# %%
band_subset = df[df["capacity_band"] == "8kW to 10kW"]

# %%
# remove outliers
q1 = band_subset["cost"].quantile(0.25)
q3 = band_subset["cost"].quantile(0.75)
iqr = q3 - q1
lower = q1 - 1.5 * iqr
upper = q3 + 1.5 * iqr

band_clean = band_subset[(band_subset["cost"] >= lower) & (band_subset["cost"] <= upper)]

# %%
fig, ax = plt.subplots(figsize=(6, 6))
ax.boxplot(band_subset["cost"].dropna(), vert=True)

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
print("\n--- 8kW to 10kW ---")
print(f"n = {len(band_clean)}")

# Numerical fields
print("\n--- Cost ---")
print(band_clean["cost"].describe())

print("\n--- Space heat demand ---")
print(band_clean["heat_demand"].describe())

print("\n--- DHW heat demand ---")
print(band_clean["water_demand"].describe())

print("\n--- SCOP ---")
print(band_clean["scop"].describe())

print("\n--- Number of habitable rooms ---")
print(band_clean["NUMBER_HABITABLE_ROOMS"].describe())
print(band_clean["NUMBER_HABITABLE_ROOMS"].value_counts(normalize=True).sort_index() * 100)

# Categorical fields
print("\n--- Built form ---")
print(band_clean["BUILT_FORM"].value_counts(normalize=True).round(3) * 100)

print("\n--- Property type ---")
print(band_clean["PROPERTY_TYPE"].value_counts(normalize=True).round(3) * 100)

# %% [markdown]
# Anchoring to median cost

# %%
median_cost = band_clean["cost"].median()
print(median_cost)

# %%
band_clean = band_clean.copy()
band_clean["_dist"] = (band_clean["cost"] - median_cost).abs()

min_dist = band_clean["_dist"].min()
tied_rows = band_clean[band_clean["_dist"] == min_dist]

print(f"{len(tied_rows)} row(s) tied at minimum distance")
print(tied_rows[["cost", "heat_demand", "NUMBER_HABITABLE_ROOMS", "BUILT_FORM", "PROPERTY_TYPE", "_dist"]])

# %% [markdown]
# Anchoring to median demand

# %%
median_demand = band_clean["heat_demand"].median()
print(median_demand)

# %%
band_clean = band_clean.copy()
band_clean["_dist"] = (band_clean["heat_demand"] - median_demand).abs()

min_dist = band_clean["_dist"].min()
tied_rows = band_clean[band_clean["_dist"] == min_dist]

print(f"{len(tied_rows)} row(s) tied at minimum distance")
print(tied_rows[["cost", "heat_demand", "NUMBER_HABITABLE_ROOMS", "BUILT_FORM", "PROPERTY_TYPE", "_dist"]])

# %% [markdown]
# ---

# %% [markdown]
# 6 to 8 kW

# %%
band_subset = df[df["capacity_band"] == "6kW to 8kW"]

# %%
# removing outliers
q1 = band_subset["cost"].quantile(0.25)
q3 = band_subset["cost"].quantile(0.75)
iqr = q3 - q1
lower = q1 - 1.5 * iqr
upper = q3 + 1.5 * iqr

band_clean = band_subset[(band_subset["cost"] >= lower) & (band_subset["cost"] <= upper)]

# %%
fig, ax = plt.subplots(figsize=(6, 6))
ax.boxplot(band_subset["cost"].dropna(), vert=True)

ax.set_ylabel("Installed cost (£)")
ax.set_title("Cost distribution for 6kW to 8kW band (n={})".format(len(band_subset)))
ax.set_xticklabels(["6kW to 8kW"])

# Overlay the IQR bounds as reference lines
ax.axhline(lower, color="firebrick", linestyle="--", linewidth=1, label=f"Lower bound (£{lower:,.0f})")
ax.axhline(upper, color="firebrick", linestyle="--", linewidth=1, label=f"Upper bound (£{upper:,.0f})")
ax.legend(fontsize=8)

plt.tight_layout()

plt.show()

# %%
print("\n--- 6kW to 8kW ---")
print(f"n = {len(band_clean)}")

# Numerical fields
print("\n--- Cost ---")
print(band_clean["cost"].describe())

print("\n--- Space heat demand ---")
print(band_clean["heat_demand"].describe())

print("\n--- DHW heat demand ---")
print(band_clean["water_demand"].describe())

print("\n--- SCOP ---")
print(band_clean["scop"].describe())

print("\n--- Number of habitable rooms ---")
print(band_clean["NUMBER_HABITABLE_ROOMS"].describe())
print(band_clean["NUMBER_HABITABLE_ROOMS"].value_counts(normalize=True).sort_index() * 100)

# Categorical fields
print("\n--- Built form ---")
print(band_clean["BUILT_FORM"].value_counts(normalize=True).round(3) * 100)

print("\n--- Property type ---")
print(band_clean["PROPERTY_TYPE"].value_counts(normalize=True).round(3) * 100)

# %% [markdown]
# Anchoring to median cost

# %%
median_cost = band_clean["cost"].median()

band_clean = band_clean.copy()
band_clean["_dist"] = (band_clean["cost"] - median_cost).abs()

min_dist = band_clean["_dist"].min()
tied_rows = band_clean[band_clean["_dist"] == min_dist]

print(f"{len(tied_rows)} row(s) tied at minimum distance")
print(tied_rows[["cost", "heat_demand", "NUMBER_HABITABLE_ROOMS", "BUILT_FORM", "PROPERTY_TYPE", "_dist"]])

# %% [markdown]
# Anchoring to median demand

# %%
median_demand = band_clean["heat_demand"].median()

band_clean = band_clean.copy()
band_clean["_dist"] = (band_clean["heat_demand"] - median_demand).abs()

min_dist = band_clean["_dist"].min()
tied_rows = band_clean[band_clean["_dist"] == min_dist]

print(f"{len(tied_rows)} row(s) tied at minimum distance")
print(tied_rows[["cost", "heat_demand", "NUMBER_HABITABLE_ROOMS", "BUILT_FORM", "PROPERTY_TYPE", "_dist"]])

# %% [markdown]
# ---

# %% [markdown]
# 10 to 12 kW

# %%
band_subset = df[df["capacity_band"] == "10kW to 12kW"]

# %%
# removing outliers
q1 = band_subset["cost"].quantile(0.25)
q3 = band_subset["cost"].quantile(0.75)
iqr = q3 - q1
lower = q1 - 1.5 * iqr
upper = q3 + 1.5 * iqr

band_clean = band_subset[(band_subset["cost"] >= lower) & (band_subset["cost"] <= upper)]

# %%
fig, ax = plt.subplots(figsize=(6, 6))
ax.boxplot(band_subset["cost"].dropna(), vert=True)

ax.set_ylabel("Installed cost (£)")
ax.set_title("Cost distribution for 10kW to 12kW band (n={})".format(len(band_subset)))
ax.set_xticklabels(["10kW to 12kW"])

# Overlay the IQR bounds as reference lines
ax.axhline(lower, color="firebrick", linestyle="--", linewidth=1, label=f"Lower bound (£{lower:,.0f})")
ax.axhline(upper, color="firebrick", linestyle="--", linewidth=1, label=f"Upper bound (£{upper:,.0f})")
ax.legend(fontsize=8)

plt.tight_layout()

plt.show()

# %%
print("\n--- 10kW to 12kW ---")
print(f"n = {len(band_clean)}")

# Numerical fields
print("\n--- Cost ---")
print(band_clean["cost"].describe())

print("\n--- Space heat demand ---")
print(band_clean["heat_demand"].describe())

print("\n--- DHW heat demand ---")
print(band_clean["water_demand"].describe())

print("\n--- SCOP ---")
print(band_clean["scop"].describe())

print("\n--- Number of habitable rooms ---")
print(band_clean["NUMBER_HABITABLE_ROOMS"].describe())
print(band_clean["NUMBER_HABITABLE_ROOMS"].value_counts(normalize=True).sort_index() * 100)

# Categorical fields
print("\n--- Built form ---")
print(band_clean["BUILT_FORM"].value_counts(normalize=True).round(3) * 100)

print("\n--- Property type ---")
print(band_clean["PROPERTY_TYPE"].value_counts(normalize=True).round(3) * 100)

# %% [markdown]
# Anchoring to median cost

# %%
median_cost = band_clean["cost"].median()

band_clean = band_clean.copy()
band_clean["_dist"] = (band_clean["cost"] - median_cost).abs()

min_dist = band_clean["_dist"].min()
tied_rows = band_clean[band_clean["_dist"] == min_dist]

print(f"{len(tied_rows)} row(s) tied at minimum distance")
print(tied_rows[["cost", "heat_demand", "capacity", "NUMBER_HABITABLE_ROOMS", "BUILT_FORM", "PROPERTY_TYPE", "_dist"]])

# %% [markdown]
# Anchoring to median demand

# %%
median_demand = band_clean["heat_demand"].median()

band_clean = band_clean.copy()
band_clean["_dist"] = (band_clean["heat_demand"] - median_demand).abs()

min_dist = band_clean["_dist"].min()
tied_rows = band_clean[band_clean["_dist"] == min_dist]

print(f"{len(tied_rows)} row(s) tied at minimum distance")
print(tied_rows[["cost", "heat_demand", "capacity", "NUMBER_HABITABLE_ROOMS", "BUILT_FORM", "PROPERTY_TYPE", "_dist"]])
