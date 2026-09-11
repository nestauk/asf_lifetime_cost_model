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
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from asf_lifetime_cost_model.getters.getter_utils import _read_s3_csv_to_dataframe

# %%
# Only interested in installs in current year
current_year = datetime.datetime.now().year

# %% [markdown]
# ### MCS installations data only
# - This step is to check number of installs when filtering fields of interest and compare with what we get from the MCS-EPC joined data

# %%
mcs_df = _read_s3_csv_to_dataframe(bucket_name="asf-core-data", s3_key="outputs/MCS/mcs_installations_260716.csv")

# %%
#  Ensure commission_date is in datetime format
mcs_df["commission_date"] = pd.to_datetime(mcs_df["commission_date"])

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
# mcs_epc_df.to_pickle("mcs_epc_df_temp.pkl")
# mcs_epc_df = pd.read_pickle("mcs_epc_df_temp.pkl")

# %% [markdown]
# Data fields of interest (MCS):
# - `commission_date`
# - `capacity`: Total installed capacity (kW)
# - `estimated_annual_generation`: Estimated energy produced in a year (kWh)
# - `scop`
# - `heat_demand` and `water_demand` (Note: `capacity` = `heat_demand`): Annual space heating requirement (kWh/year), Annual water heating requirement (kWh/year)
# - `design = Space heat and DHW`
# - `cost`
# - `installation_type = Domestic`
# - `Project Type = Retrofit`
# - `tech_type = Air Source Heat Pump`
#
# Data fields of interest (EPC):
# - `NUMBER_HABITABLE_ROOMS`
# - `BUILT_FORM`
# - `PROPERTY_TYPE`
# - `MAINHEAT_DESCRIPTION = Boiler and radiators, mains gas`

# %%
#  Ensure commission_date is in datetime format
mcs_epc_df["commission_date"] = pd.to_datetime(mcs_epc_df["commission_date"])

df = mcs_epc_df[
    (mcs_epc_df["tech_type"] == "Air Source Heat Pump")
    & (mcs_epc_df["installation_type"] == "Domestic")
    & (mcs_epc_df["Project Type"] == "Retrofit")
    # & (mcs_epc_df["commission_date"].dt.year == current_year)
    & (mcs_epc_df["MAINHEAT_DESCRIPTION"] == "Boiler and radiators, mains gas")
    & (mcs_epc_df["design"] == "Space heat and DHW")
].copy()

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
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(pct_breakdown.index, pct_breakdown.values, color="#4C72B0", edgecolor="white")

ax.set_ylabel("% of installations")
ax.set_xlabel("Capacity band (kW)")
ax.set_title("Distribution of capacity of ASHPs installed (historical)")
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
# Current year only

# %%
#  Ensure commission_date is in datetime format
mcs_epc_df["commission_date"] = pd.to_datetime(mcs_epc_df["commission_date"])

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
df["commission_date"].unique()

# %% [markdown]
# Characterising installs by capacity bands used in BUS reporting
# - We're assuming that heat pumps are sized primarily based on property heat demand
# - Considering different capacity bands == different property heat demand levels == different property types

# %%
df[["heat_demand", "capacity"]].corr()

# %%
df["capacity"].describe()

# %%
df["capacity"].mode()

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
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(pct_breakdown.index, pct_breakdown.values, color="#4C72B0", edgecolor="white")

ax.set_ylabel("% of installations")
ax.set_xlabel("Capacity band (kW)")
ax.set_title("Distribution of capacity of ASHPs installed in 2026")
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
# - Clear overall ordering -> larger capacity bands  have  higher typical heat demand
# - Heat demand is well separated between bands at the low end (0–14kW), but overlaps heavily at the high end (14kW+)
# - The overlap at the high end is likely due to small sample size (14kW+ bands make up <5% of installations), not necessarily real variability
# - Most data (~94%) sits in the 4–14kW range, this is where "typical household" estimates are most reliable

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
# - Unlike heat demand, installation cost does not clearly increase with capacity band — most bands cluster in a similar £10k–£20k range
# - Matches earlier weak cost/heat-demand correlation (0.148), cost is driven by something other than system size alone
# - Clear extreme outlier around £110k–£120k (10–12kW band) (data hasn't been cleaned yet, should be cleaned before drawing conclusions)
# - Less populated bands (18–20kW, >20kW) show wider spread (likely a small-sample effect)

# %% [markdown]
# #### Estimating typical heat demand and install cost for each capacity band

# %% [markdown]
# #### 8 to 10 kW
# - Most common capacity band

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

# %%
print(f"Median cost: {band_clean['cost'].median()}")
print(f"Median space heating demand (kWh/year): {band_clean['heat_demand'].median()}")
print(f"Median DHW demand (kWh/year): {band_clean['water_demand'].median()}")

# %% [markdown]
# Ref check: BUS Statistics May 2026 2025/26 median installation cost for this capacity band = £12,658

# %% [markdown]
# Identifying an anchor household(s) closest to median cost

# %%
median_cost = band_clean["cost"].median()

band_clean = band_clean.copy()
band_clean["_dist"] = (band_clean["cost"] - median_cost).abs()

min_dist = band_clean["_dist"].min()
tied_rows = band_clean[band_clean["_dist"] == min_dist]

print(f"{len(tied_rows)} row(s) tied at minimum distance")
print(
    tied_rows[["cost", "heat_demand", "water_demand", "NUMBER_HABITABLE_ROOMS", "BUILT_FORM", "PROPERTY_TYPE", "_dist"]]
)

# %% [markdown]
# Identifying an anchor household(s) closest to median heat demand

# %%
median_demand = band_clean["heat_demand"].median()
band_clean = band_clean.copy()
band_clean["_dist"] = (band_clean["heat_demand"] - median_demand).abs()

min_dist = band_clean["_dist"].min()
tied_rows = band_clean[band_clean["_dist"] == min_dist]

print(f"{len(tied_rows)} row(s) tied at minimum distance")
print(
    tied_rows[["cost", "heat_demand", "water_demand", "NUMBER_HABITABLE_ROOMS", "BUILT_FORM", "PROPERTY_TYPE", "_dist"]]
)

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

# %%
print(f"Median cost: {band_clean['cost'].median()}")
print(f"Median space heating demand (kWh/year): {band_clean['heat_demand'].median()}")
print(f"Median DHW demand (kWh/year): {band_clean['water_demand'].median()}")

# %% [markdown]
# Ref check: BUS Statistics May 2026 2025/26 median installation cost for this capacity band = £12,158

# %% [markdown]
# Identifying an anchor household(s) closest to median cost

# %%
median_cost = band_clean["cost"].median()

band_clean = band_clean.copy()
band_clean["_dist"] = (band_clean["cost"] - median_cost).abs()

min_dist = band_clean["_dist"].min()
tied_rows = band_clean[band_clean["_dist"] == min_dist]

print(f"{len(tied_rows)} row(s) tied at minimum distance")
print(
    tied_rows[["cost", "heat_demand", "water_demand", "NUMBER_HABITABLE_ROOMS", "BUILT_FORM", "PROPERTY_TYPE", "_dist"]]
)

# %% [markdown]
# Identifying an anchor household(s) closest to median heat demand

# %%
median_demand = band_clean["heat_demand"].median()
band_clean = band_clean.copy()
band_clean["_dist"] = (band_clean["heat_demand"] - median_demand).abs()

min_dist = band_clean["_dist"].min()
tied_rows = band_clean[band_clean["_dist"] == min_dist]

print(f"{len(tied_rows)} row(s) tied at minimum distance")
print(
    tied_rows[["cost", "heat_demand", "water_demand", "NUMBER_HABITABLE_ROOMS", "BUILT_FORM", "PROPERTY_TYPE", "_dist"]]
)

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

# %%
print(f"Median cost: {band_clean['cost'].median()}")
print(f"Median space heating demand (kWh/year): {band_clean['heat_demand'].median()}")
print(f"Median DHW demand (kWh/year): {band_clean['water_demand'].median()}")

# %% [markdown]
# Ref check: BUS Statistics May 2026 2025/26 median installation cost for this capacity band = £13,940

# %% [markdown]
# Identifying an anchor household(s) closest to median cost

# %%
median_cost = band_clean["cost"].median()

band_clean = band_clean.copy()
band_clean["_dist"] = (band_clean["cost"] - median_cost).abs()

min_dist = band_clean["_dist"].min()
tied_rows = band_clean[band_clean["_dist"] == min_dist]

print(f"{len(tied_rows)} row(s) tied at minimum distance")
print(
    tied_rows[["cost", "heat_demand", "water_demand", "NUMBER_HABITABLE_ROOMS", "BUILT_FORM", "PROPERTY_TYPE", "_dist"]]
)

# %% [markdown]
# Identifying an anchor household(s) closest to median heat demand

# %%
median_demand = band_clean["heat_demand"].median()
band_clean = band_clean.copy()
band_clean["_dist"] = (band_clean["heat_demand"] - median_demand).abs()

min_dist = band_clean["_dist"].min()
tied_rows = band_clean[band_clean["_dist"] == min_dist]

print(f"{len(tied_rows)} row(s) tied at minimum distance")
print(
    tied_rows[["cost", "heat_demand", "water_demand", "NUMBER_HABITABLE_ROOMS", "BUILT_FORM", "PROPERTY_TYPE", "_dist"]]
)
