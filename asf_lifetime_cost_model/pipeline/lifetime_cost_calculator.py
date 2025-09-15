"""A module to calculate the lifetime cost of heating systems.

This includes installation, maintenance, and running costs.

Example of usage:
"""

# package imports
from typing import Optional, Union

import pandas as pd

# local imports
from asf_lifetime_cost_model import config
from asf_lifetime_cost_model.getters import data_getters
from asf_lifetime_cost_model.pipeline.maintenance_and_installation_costs import (
    compute_cost_with_loan,
    create_cost_reduction_data,
    get_ashp_subsidy_value,
)
from asf_lifetime_cost_model.pipeline.running_costs import (
    create_energy_cost_time_series,
    get_wholesale_price_projection_series,
)


class LifetimeCostCalculator(object):
    """A class to calculate the lifetime cost of heating systems, including installation, maintenance, and running costs."""

    def __init__(self):
        self.ashp_installation_costs = data_getters.get_ashp_installation_costs()
        self.boiler_installation_costs = data_getters.get_gas_boiler_installation_costs()
        self.ashp_subsidy_options_data = data_getters.get_ashp_subsidy_options_data()
        self.wholesale_price_projections = data_getters.get_desnz_wholesale_price_projections()
        self.property_heat_demand = data_getters.get_property_heat_demand()
        self.property_archetypes = self.property_heat_demand.index.tolist()

    def compute_total_maintenance_cost(
        self, maintenance_cost: float, maintenance_frequency_per_year: float, life_span: int
    ) -> pd.DataFrame:
        """Computes the total maintenance cost for different property archetypes.

        Args:
            maintenance_cost (float): The cost of one maintenance servicing session for heating system.
            maintenance_frequency_per_year (float): Average number of times the heating system is serviced each year.
            life_span (int): Number of years the heating system is assumed to be operational.

        Returns:
            pd.DataFrame: A DataFrame with property archetypes as index and total maintenance cost as column.
        """
        maintenance_costs = pd.DataFrame(index=self.property_archetypes, columns=["maintenance_cost"])
        maintenance_costs["maintenance_cost"] = maintenance_cost * maintenance_frequency_per_year * life_span
        return maintenance_costs

    def compute_upfront_cost(
        self,
        heating_system: str,
        annual_cost_reduction: float,
        purchase_year: int,
        life_span: int = None,
        decile: int = None,
        installation_costs: pd.DataFrame = None,
        subsidy_model_or_input_values: Union[str, dict] = "no subsidy",
        purchase_with_loan: bool = False,
        loan_interest_rate: float = 0.0,
    ) -> pd.DataFrame:
        """Computes the upfront costs of installing a heating system.

        Args:
            heating_system (str): heating system.
                Takes "ashp" (for air source heat pump) or "boiler" (for gas boiler).
            annual_cost_reduction (float): how much the cost of installing the heating system reduces each year
                in comparison to the previous year. 5% reduction should be inputted as 0.05.
            purchase_year (int): the year in which the heating system is purchased and installed.
            life_span (int): Number of years the heating system is assumed to be operational.
                Defaults to None. Only required when purchase_with_loan is True.
            decile (int, optional): cost decile, only used for air source heat pumps.
            installation_costs (pd.DataFrame, optional): DataFrame containing installation costs for different property archetypes.
            subsidy_model_or_input_values (Union[str, dict], optional): The ASHP subsidy model to get the subsidy
                to be subtracted OR a dictionary of subsidy values for each year.
                Models include: "flat", "slow stepdown", "fast stepdown", "high", "zero from 2028",
                "smallest", "no subsidy".
            purchase_with_loan (bool): Whether heating system is purchased with a loan. Defaults to False.
                Loan repayment period is set equal to provided life span of heating system.
            loan_interest_rate (float): Loan interest rate, as a decimal (e.g. 5% interest rate should be inputted
                as 0.05). Defaults to 0.0.

        Raises:
            ValueError: If the heating system inputed is not supported or the year is above or equal to 2035.

        Returns:
            float: Upfront cost of installing a heating system.
        """
        if purchase_year >= config.get("installation_year_max"):
            raise ValueError(f"Purchase year must be before {config.get('installation_year_max')}.")

        if heating_system not in ["ashp", "boiler"]:
            raise ValueError(
                f"Unsupported heating system: {heating_system}. Supported heating systems are `ashp` and `boiler`."
            )

        if (heating_system == "boiler") and (subsidy_model_or_input_values != "no subsidy"):
            raise ValueError("Subsidy model is only applicable for air source heat pumps. Choose 'no subsidy'.")

        if installation_costs is None:
            installation_costs = (
                self.ashp_installation_costs.copy()
                if heating_system == "ashp"
                else self.boiler_installation_costs.copy()
            )
        installation_costs = data_getters.get_installation_cost(
            costs_data=installation_costs, heating_system=heating_system, decile=decile
        )

        # Apply installation cost reduction assumption
        cost_reduction_data = create_cost_reduction_data(annual_cost_reduction=annual_cost_reduction)
        cost_reduction_value = cost_reduction_data[purchase_year]
        installation_costs["installation_cost"] = installation_costs["installation_cost"] * cost_reduction_value

        # ASHP with preset subsidy model
        if (type(subsidy_model_or_input_values) is str) and (heating_system == "ashp"):
            subsidy_data = self.ashp_subsidy_options_data.copy()
            subsidy_value = get_ashp_subsidy_value(
                subsidy_data=subsidy_data, subsidy_model=subsidy_model_or_input_values, purchase_year=purchase_year
            )
            installation_costs["installation_cost"] = installation_costs["installation_cost"] - subsidy_value
        # ASHP with custom subsidy model
        elif heating_system == "ashp":  # dictionary provided
            if purchase_year not in subsidy_model_or_input_values.keys():
                raise ValueError(f"Please provide subsidy value for purchase year: {purchase_year}")
            installation_costs["installation_cost"] = (
                installation_costs["installation_cost"] - subsidy_model_or_input_values[purchase_year]
            )

        if purchase_with_loan:
            if life_span is None:
                raise ValueError("Please provide `life_span` in years when purchasing with loans.")

            if loan_interest_rate < 0.0 or loan_interest_rate > 1.0:
                raise ValueError("Loan interest rate should be provided as a decimal between 0 and 1.")

            installation_costs["installation_cost"] = installation_costs.apply(
                lambda x: compute_cost_with_loan(
                    upfront_cost=x["installation_cost"], life_span=life_span, loan_interest_rate=loan_interest_rate
                ),
                axis=1,
            )

        return installation_costs

    def compute_running_cost_time_series(
        self,
        purchase_year: int,
        life_span: int,
        heating_system_efficiency: float,
        fuel_type: str,
        wholesale_price_projection_scenario: str,
        include_standing_charge: bool,
        levy_rebalancing: bool,
        levies_to_rebalance: Optional[list[str]] = None,
        levy_rebalancing_weights: Optional[dict[str, float]] = None,
        include_vat: bool = True,
    ) -> pd.DataFrame:
        """Creates a time series of total running costs for specified heating system in each year of operation.

        Args:
            purchase_year (int): Year of purchase (i.e. installation), valid arguments are [2025, 2035].
            life_span (int): Number of years assumed to be operational.
            heating_system_efficiency (float): Assumed efficiency of heating system, expressed as a ratio.
                e.g. 1.0 means 100% efficient, 0.85 means 85% efficient, and
                3.0 means 300% efficient (i.e. the system produces 3 units of heat per 1 unit of input energy).
            fuel_type (str): Fuel type, valid arguments are "electricity" or "gas".
            wholesale_price_projection_scenario (str): Name of DESNZ projection scenario.
                Valid arguments are "reference", "low fossil fuel prices", "high fossil fuel prices",
                "low economic growth", "high economic growth", "existing policies only"
            include_standing_charge (bool): Whether annual standing charge should be included in running costs.
            levy_rebalancing (bool): Whether a levy rebalancing scenario is to be applied.
            levies_to_rebalance (Optional[list[str]], optional): List containing short names of levies to be rebalanced
                with provided weights. Defaults to None.
            levy_rebalancing_weights (Optional[dict[str, float]], optional): Dictionary containing rebalancing weights
                to be applied to all levies provided in levies_to_rebalance, where keys are:
                "electricity_weight", "gas_weight", "tax_weight", "fixed_electricity_weight", "variable_electricity_weight",
                "fixed_gas_weight" and values are revenue proprortions [0, 1]. Defaults to None.
            include_vat (bool): Whether 5% VAT is included in energy prices. Defaults to True.

        Returns:
            pd.DataFrame: columns are years of operation and values are total running costs (£) in each year,
                each row is a different property archetype.
        """
        heat_demand_data = self.property_heat_demand.copy()

        # Calculate annual energy demand of heating system
        heat_demand_data["energy_demand"] = heat_demand_data["heat_demand"] / heating_system_efficiency

        ### Create energy tariff for each year of operation ###

        # Instantiate Tariff objects for latest price cap
        gas_tariff, electricity_tariff = data_getters.get_current_energy_price_cap_tariffs()

        # Apply levy rebalancing scenario to latest policy costs
        if levy_rebalancing:
            # Rebalancing weights are applied to all provided levies
            rebalanced_levies = data_getters.get_rebalanced_levies(
                levies_to_rebalance=levies_to_rebalance,
                electricity_weight=levy_rebalancing_weights["electricity_weight"],
                gas_weight=levy_rebalancing_weights["gas_weight"],
                tax_weight=levy_rebalancing_weights["tax_weight"],
                variable_electricity_weight=levy_rebalancing_weights["variable_electricity_weight"],
                fixed_electricity_weight=levy_rebalancing_weights["fixed_electricity_weight"],
                variable_gas_weight=levy_rebalancing_weights["variable_gas_weight"],
                fixed_gas_weight=levy_rebalancing_weights["fixed_gas_weight"],
                price_cap_period="LATEST",
            )
            gas_tariff = gas_tariff.update_policy_costs(rebalanced_levies)
            electricity_tariff = electricity_tariff.update_policy_costs(rebalanced_levies)

        # Create list of operating years
        years_of_operation = list(range(purchase_year, purchase_year + life_span))

        # Create a dictionary of gas and electricity tariffs for each year of operation
        # Note we are using the same tariff for each year in the future
        gas_tariff_time_series = dict.fromkeys(years_of_operation, gas_tariff)
        electricity_tariff_time_series = dict.fromkeys(years_of_operation, electricity_tariff)

        ### Get wholesale price projections ###
        # Get wholesale price projection time series for fuel and scenario of interest
        wholesale_prices_series_df = get_wholesale_price_projection_series(
            wholesale_prices_data_all_scenarios=self.wholesale_price_projections.copy(),
            fuel_type=fuel_type,
            projection_scenario=wholesale_price_projection_scenario,
        )

        ### Aggregate tariff cost components to replace wholesale price with projection ###

        # Wholesale costs include DF and CM tariff cost components
        # We need to aggregate the tariff cost components by broader categories to be able to
        # replace the wholesale costs with the projection for that year

        # Gas costs
        gas_unit_cost_time_series, gas_standing_charge_time_series = create_energy_cost_time_series(
            tariff_time_series=gas_tariff_time_series,
            fuel_type="gas",
            wholesale_prices_series=wholesale_prices_series_df,
        )

        # Electricity costs
        electricity_unit_cost_time_series, electricity_standing_charge_time_series = create_energy_cost_time_series(
            tariff_time_series=electricity_tariff_time_series,
            fuel_type="electricity",
            wholesale_prices_series=wholesale_prices_series_df,
        )

        if include_vat:
            for cost_time_series in [
                gas_unit_cost_time_series,
                gas_standing_charge_time_series,
                electricity_unit_cost_time_series,
                electricity_standing_charge_time_series,
            ]:
                for year in cost_time_series:
                    cost_time_series[year] *= 1.05

        ### Compute total running cost in each year of operation ###
        running_costs_time_series = pd.DataFrame()
        for year in years_of_operation:
            if fuel_type == "gas":
                running_costs_time_series[year] = gas_unit_cost_time_series[year] * (
                    heat_demand_data["energy_demand"] / 1_000
                )  # convert energy_demand in kWh/year to MWh/year

                if include_standing_charge:
                    running_costs_time_series[year] += gas_standing_charge_time_series[year]

            else:  # fuel_type is electricity
                running_costs_time_series[year] = electricity_unit_cost_time_series[year] * (
                    heat_demand_data["energy_demand"] / 1_000
                )

                if include_standing_charge:
                    running_costs_time_series[year] += electricity_standing_charge_time_series[year]

        return running_costs_time_series

    def compute_total_lifetime_costs(
        self, installation_costs: pd.DataFrame, maintenance_costs: pd.DataFrame, running_costs: pd.DataFrame
    ) -> pd.DataFrame:
        """Computes the lifetime cost of a heating system over its lifetime.

        Args:
            installation_costs (pd.DataFrame): DataFrame containing installation costs for different property archetypes.
            maintenance_costs (pd.DataFrame): DataFrame containing total maintenance costs for different property archetypes.
            running_costs (pd.DataFrame): DataFrame containing total running costs for different property archetypes in each year of operation.

        Returns:
            pd.DataFrame: A DataFrame with property archetypes as index and total lifetime costs as column.
        """
        total_lifetime_costs = pd.DataFrame()
        total_lifetime_costs["lifetime_installation_costs"] = installation_costs.sum(axis=1)
        total_lifetime_costs["lifetime_maintenance_costs"] = maintenance_costs
        total_lifetime_costs["lifetime_running_costs"] = running_costs.sum(axis=1)
        total_lifetime_costs["total_lifetime_costs"] = total_lifetime_costs.sum(axis=1)

        return total_lifetime_costs

    # def create_annualised_cost_time_series(self,
    #                                        cost_value: float, life_span: int, purchase_year: int) -> dict:
    #     """Creates a time series of annualised cost per year in the lifetime of the heating system.

    #     Args:
    #         cost_value (float): The total cost value to be annualised.
    #         life_span (int): Number of years the heating system is assumed to be operational.
    #         purchase_year (int): The year in which the heating system is purchased and installed.

    #     Returns:
    #         dict: A dictionary with years as keys and cost values as values.
    #     """
    #     cost_per_year = cost_value / life_span
    #     annualised_cost_time_series = dict.fromkeys(
    #         range(purchase_year, purchase_year + life_span),
    #         cost_per_year,
    #     )

    #     return annualised_cost_time_series

    # def calculate_median_archetype_cost(self):
    #     pass
