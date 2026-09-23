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
# ---

# %% [markdown]
# ## Identifying average heat demand and install cost for a 'typical' household installing an ASHP

# %% [markdown]
# Last updated: 23/09/2026

# %%
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from asf_lifetime_cost_model.getters.getter_utils import _read_s3_csv_to_dataframe

# %% [markdown]
# ### MCS installations data only
# - This step is to check number of installs when filtering fields of interest and compare with what we get from the MCS-EPC joined data

# %%
mcs_df = _read_s3_csv_to_dataframe(bucket_name="asf-core-data", s3_key="outputs/MCS/mcs_installations_260911.csv")

# %%
# mcs_installations_260911.csv has up to 2026 Q1 only
print(mcs_df["commission_date"].min(), mcs_df["commission_date"].max())

# %%
#  Ensure commission_date is in datetime format
mcs_df["commission_date"] = pd.to_datetime(mcs_df["commission_date"])

mcs_filtered_df = mcs_df[
    (mcs_df["tech_type"] == "Air Source Heat Pump")
    & (mcs_df["installation_type"] == "Domestic")
    & (mcs_df["Project Type"] == "Retrofit")
    & (
        ((mcs_df["commission_date"].dt.year == 2025) & (mcs_df["commission_date"].dt.quarter.isin([3, 4])))
        | ((mcs_df["commission_date"].dt.year == 2026) & (mcs_df["commission_date"].dt.quarter.isin([1, 2])))
    )
    & (mcs_df["design"] == "Space heat and DHW")
].copy()

# %%
# Checking how many installs in FY 2025/26
len(mcs_filtered_df)

# %% [markdown]
# ### MCS and EPC joined data

# %%
mcs_epc_df = _read_s3_csv_to_dataframe(
    bucket_name="asf-core-data", s3_key="outputs/MCS/mcs_installations_epc_most_relevant_260911.csv"
)

# %%
# mcs_installations_epc_most_relevant_260911.csv has up to 2026 Q1 only
print(mcs_epc_df["commission_date"].min(), mcs_epc_df["commission_date"].max())
print(mcs_epc_df["INSPECTION_DATE"].min(), mcs_epc_df["INSPECTION_DATE"].max())

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

# %% [markdown]
# No commission date filter (all historical)

# %%
#  Ensure commission_date is in datetime format
mcs_epc_df["commission_date"] = pd.to_datetime(mcs_epc_df["commission_date"])

df = mcs_epc_df[
    (mcs_epc_df["tech_type"] == "Air Source Heat Pump")
    & (mcs_epc_df["installation_type"] == "Domestic")
    & (mcs_epc_df["Project Type"] == "Retrofit")
    & (mcs_epc_df["MAINHEAT_DESCRIPTION"] == "Boiler and radiators, mains gas")
    & (mcs_epc_df["design"] == "Space heat and DHW")
].copy()

# %%
# Add total heat demand and clean physical extremes
df["total_heat_demand"] = df["heat_demand"] + df["water_demand"]
df = df[df["total_heat_demand"] <= 100_000]

# %%
df["total_heat_demand"].describe()

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
# Financial year 2025/26 only

# %%
df = mcs_epc_df[
    (mcs_epc_df["tech_type"] == "Air Source Heat Pump")
    & (mcs_epc_df["installation_type"] == "Domestic")
    & (mcs_epc_df["Project Type"] == "Retrofit")
    & (
        ((mcs_epc_df["commission_date"].dt.year == 2025) & (mcs_epc_df["commission_date"].dt.quarter.isin([3, 4])))
        | ((mcs_epc_df["commission_date"].dt.year == 2026) & (mcs_epc_df["commission_date"].dt.quarter.isin([1, 2])))
    )
    & (mcs_epc_df["design"] == "Space heat and DHW")
    & (mcs_epc_df["MAINHEAT_DESCRIPTION"] == "Boiler and radiators, mains gas")
].copy()

# %%
# Add total heat demand and clean physical extremes
df["total_heat_demand"] = df["heat_demand"] + df["water_demand"]
df = df[df["total_heat_demand"] <= 100_000]

# %%
df["total_heat_demand"].describe()

# %% [markdown]
# Characterising installs by capacity bands used in BUS reporting
# - We're assuming that heat pumps are sized primarily based on property heat demand
# - Considering different capacity bands == different property heat demand levels == different property types

# %%
df[["heat_demand", "capacity"]].corr()  # space heating only

# %%
df["capacity"].describe()

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
ax.set_title("Distribution of capacity of ASHPs installed in FY 2025/26 (Q1 2026 only)")
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
# - The overlap at the high end is likely due to small sample size (14kW+ bands make up <4% of installations), not necessarily real variability
# - Most data (~93%) sits in the 4–14kW range, this is where "typical household" estimates are most reliable

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
print(f"Median SCOP: {band_clean['scop'].median()}")

# %% [markdown]
# Interpretation: Installation cost and heat demand of a typical household *installing a heat pump in FY 2025/26*. This is not the same as the average household. We need to acknowledge that the typical household currently getting heat pumps do skew towards bigger households.

# %% [markdown]
# Ref check: BUS Statistics May 2026 2025/26 median installation cost for this capacity band = £12,658

# %% [markdown]
# **Using EPC property descriptors to describe the likely physical characteristics of this 'typical' household**

# %% [markdown]
# Use median heat demand to identify neighbouring properties and examine probabilistic property profile

# %%
median_space_heat_demand = band_clean["heat_demand"].median()
median_dhw_demand = band_clean["water_demand"].median()  # domestic hot water

# Compute two-dimensional distance (space heat and DHW)
space_sd = band_clean["heat_demand"].std()
dhw_sd = band_clean["water_demand"].std()
band_clean["distance"] = np.sqrt(
    ((band_clean["heat_demand"] - median_space_heat_demand) / space_sd) ** 2
    + ((band_clean["water_demand"] - median_dhw_demand) / dhw_sd) ** 2
)

# %% [markdown]
# Approach 1. Simple KNN approach (K properties closest to median heat demand, weighted equally)

# %%
# Take the 50 nearest properties
K = 50
nearest = band_clean.nsmallest(K, "distance")

# %% [markdown]
# Approach 2. Kernel-weighted nearest neighbour approach

# %%
# https://pysal.org/libpysal/stable/generated/libpysal.weights.Kernel.html#libpysal.weights.Kernel


# distance scale based on k-th nearest neighbour
def compute_fixed_bandwidth(values: pd.Series, k: int = 2, eps: float = 1.0000001) -> float:
    """Compute a kernel bandwidth given an array of data."""
    x = values.sort_values(ascending=True).values
    dists = np.abs(x[:, np.newaxis] - x[np.newaxis, :])
    sorted_dists = np.sort(dists, axis=1)
    d_ik = sorted_dists[:, k]
    return np.max(d_ik) * eps


# converts distance into weight
def quartic_weights(z: pd.Series) -> pd.Series:
    """Creates quartic weights for distance data."""
    w = (15 / 16) * (1 - z**2) ** 2
    w[w > 1] = 0
    return w / w.sum() * z.shape[0]


# converts distance into weight
def gaussian_weights(z: pd.Series) -> pd.Series:
    """Creates gaussian weights for distance data."""
    w = (2 * np.pi) ** (-1 / 2) * np.exp(-(z**2) / 2)
    return w / w.sum() * z.shape[0]


# %%
# Create a bandwidth normalised distance variable.
bandwidth = compute_fixed_bandwidth(band_clean["distance"])

band_clean["_dist_z"] = band_clean["distance"] / bandwidth

# %%
# Compute weights
band_clean["quartic_weight"] = quartic_weights(band_clean["_dist_z"])
band_clean["gaussian_weight"] = gaussian_weights(band_clean["_dist_z"])

# %% [markdown]
# Comparing all approaches


# %%
def create_comparison_table(
    df: pd.DataFrame,
    epc_feature: str,
    nearest: pd.DataFrame,
) -> pd.DataFrame:

    # Quartic
    quartic = df.groupby(epc_feature)["quartic_weight"].sum().to_frame("quartic_weight")
    quartic["quartic_prop"] = quartic["quartic_weight"] / quartic["quartic_weight"].sum()

    # Gaussian
    gaussian = df.groupby(epc_feature)["gaussian_weight"].sum().to_frame("gaussian_weight")
    gaussian["gaussian_prop"] = gaussian["gaussian_weight"] / gaussian["gaussian_weight"].sum()

    # Simple KNN
    simple_knn = nearest[epc_feature].value_counts(normalize=True).to_frame("simple_knn_prop")

    # Combine
    return quartic.join(gaussian).join(simple_knn)


def create_comparison_plot(
    comparison_df: pd.DataFrame,
    epc_feature: str,
):
    comparison_df[["quartic_prop", "gaussian_prop", "simple_knn_prop"]].plot(kind="bar")
    plt.ylabel("Proportion")
    plt.xlabel(f"EPC: {epc_feature}")
    plt.title("Property type distribution at median space and domestic hot water heat demand")
    plt.xticks(rotation=45)
    plt.legend(title="Method")
    plt.tight_layout()
    return plt.show()


# %%
property_type = create_comparison_table(band_clean, "PROPERTY_TYPE", nearest)
create_comparison_plot(property_type, "PROPERTY_TYPE")

# %%
built_form = create_comparison_table(band_clean, "BUILT_FORM", nearest)
create_comparison_plot(built_form, "BUILT_FORM")

# %%
rooms = create_comparison_table(band_clean, "NUMBER_HABITABLE_ROOMS", nearest)
create_comparison_plot(rooms, "NUMBER_HABITABLE_ROOMS")
