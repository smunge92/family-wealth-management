"""
Monte Carlo Simulation for Retirement Planning
Provides probability-based retirement projections using historical market data
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Historical market return parameters (annualized)
# Based on long-term historical data from 1928-2023
ASSET_CLASS_RETURNS = {
    "stocks": {"mean": 0.10, "std": 0.18},      # S&P 500 historical
    "bonds": {"mean": 0.05, "std": 0.06},        # US Treasury bonds
    "cash": {"mean": 0.03, "std": 0.01},         # Money market/savings
    "real_estate": {"mean": 0.08, "std": 0.12},  # REITs
}

# Asset allocation by risk tolerance
RISK_ALLOCATIONS = {
    "conservative": {
        "stocks": 0.30,
        "bonds": 0.50,
        "cash": 0.15,
        "real_estate": 0.05,
    },
    "moderate": {
        "stocks": 0.50,
        "bonds": 0.30,
        "cash": 0.10,
        "real_estate": 0.10,
    },
    "aggressive": {
        "stocks": 0.70,
        "bonds": 0.15,
        "cash": 0.05,
        "real_estate": 0.10,
    },
}

# Inflation parameters
INFLATION_MEAN = 0.03
INFLATION_STD = 0.02


@dataclass
class MonteCarloResult:
    """Results from Monte Carlo simulation"""
    percentiles: Dict[int, List[float]]  # {10: [...], 25: [...], 50: [...], 75: [...], 90: [...]}
    success_rate: float  # Probability of not running out of money
    median_final_balance: float
    mean_final_balance: float
    all_projections: np.ndarray  # Full simulation data for analysis
    yearly_success_rates: List[float]  # Success rate at each year
    inflation_adjusted: bool


class MonteCarloSimulator:
    """
    Monte Carlo retirement simulation engine

    Runs thousands of simulations using randomized market returns
    to provide probability-based retirement projections.
    """

    def __init__(self, num_simulations: int = 2000, random_seed: Optional[int] = None):
        """
        Initialize the simulator

        Args:
            num_simulations: Number of simulation iterations (default 2,000)
            random_seed: Optional seed for reproducibility
        """
        self.num_simulations = num_simulations
        if random_seed is not None:
            np.random.seed(random_seed)

    def get_portfolio_return_params(self, risk_tolerance: str) -> Tuple[float, float]:
        """
        Calculate expected return and volatility for a given risk tolerance

        Args:
            risk_tolerance: "conservative", "moderate", or "aggressive"

        Returns:
            Tuple of (expected_return, volatility)
        """
        allocation = RISK_ALLOCATIONS.get(risk_tolerance, RISK_ALLOCATIONS["moderate"])

        # Calculate weighted portfolio return and variance
        portfolio_return = 0.0
        portfolio_variance = 0.0

        for asset_class, weight in allocation.items():
            params = ASSET_CLASS_RETURNS[asset_class]
            portfolio_return += weight * params["mean"]
            # Simplified variance calculation (ignoring correlations)
            portfolio_variance += (weight ** 2) * (params["std"] ** 2)

        portfolio_std = np.sqrt(portfolio_variance)

        return portfolio_return, portfolio_std

    def simulate_returns(
        self,
        years: int,
        risk_tolerance: str,
        include_inflation: bool = True
    ) -> np.ndarray:
        """
        Generate simulated annual returns for all simulations

        Args:
            years: Number of years to simulate
            risk_tolerance: Risk tolerance level
            include_inflation: Whether to adjust for inflation

        Returns:
            Array of shape (num_simulations, years) with annual returns
        """
        mean_return, std_return = self.get_portfolio_return_params(risk_tolerance)

        # Generate random returns using normal distribution
        # Shape: (num_simulations, years)
        nominal_returns = np.random.normal(
            mean_return,
            std_return,
            size=(self.num_simulations, years)
        )

        if include_inflation:
            # Generate random inflation rates
            inflation_rates = np.random.normal(
                INFLATION_MEAN,
                INFLATION_STD,
                size=(self.num_simulations, years)
            )
            # Real return = (1 + nominal) / (1 + inflation) - 1
            real_returns = (1 + nominal_returns) / (1 + inflation_rates) - 1
            return real_returns

        return nominal_returns

    def run_accumulation_simulation(
        self,
        current_savings: float,
        monthly_contribution: float,
        years: int,
        risk_tolerance: str = "moderate",
        contribution_increase_rate: float = 0.02,
        include_inflation: bool = True
    ) -> MonteCarloResult:
        """
        Run Monte Carlo simulation for retirement accumulation phase

        Args:
            current_savings: Current retirement savings balance
            monthly_contribution: Monthly contribution amount
            years: Years until retirement
            risk_tolerance: "conservative", "moderate", or "aggressive"
            contribution_increase_rate: Annual increase in contributions (default 2%)
            include_inflation: Adjust for inflation

        Returns:
            MonteCarloResult with projection data
        """
        logger.info(f"Running {self.num_simulations} accumulation simulations over {years} years")

        # Generate all returns upfront
        annual_returns = self.simulate_returns(years, risk_tolerance, include_inflation)

        # Initialize balance array: (num_simulations, years + 1)
        # +1 to include starting balance at year 0
        balances = np.zeros((self.num_simulations, years + 1))
        balances[:, 0] = current_savings

        # Run simulation year by year
        annual_contribution = monthly_contribution * 12

        for year in range(years):
            # Contribution increases each year
            year_contribution = annual_contribution * ((1 + contribution_increase_rate) ** year)

            # Apply returns and add contributions
            # Balance at end of year = (previous balance + contribution) * (1 + return)
            balances[:, year + 1] = (balances[:, year] + year_contribution) * (1 + annual_returns[:, year])

        # Calculate percentiles for each year
        percentiles = {
            10: np.percentile(balances, 10, axis=0).tolist(),
            25: np.percentile(balances, 25, axis=0).tolist(),
            50: np.percentile(balances, 50, axis=0).tolist(),
            75: np.percentile(balances, 75, axis=0).tolist(),
            90: np.percentile(balances, 90, axis=0).tolist(),
        }

        # Final balance statistics
        final_balances = balances[:, -1]

        return MonteCarloResult(
            percentiles=percentiles,
            success_rate=1.0,  # Accumulation phase always "succeeds"
            median_final_balance=float(np.median(final_balances)),
            mean_final_balance=float(np.mean(final_balances)),
            all_projections=balances,
            yearly_success_rates=[1.0] * (years + 1),
            inflation_adjusted=include_inflation
        )

    def run_withdrawal_simulation(
        self,
        starting_balance: float,
        annual_withdrawal: float,
        years: int,
        risk_tolerance: str = "moderate",
        withdrawal_increase_rate: float = 0.02,
        include_inflation: bool = True
    ) -> MonteCarloResult:
        """
        Run Monte Carlo simulation for retirement withdrawal phase

        Args:
            starting_balance: Balance at start of retirement
            annual_withdrawal: Annual withdrawal amount
            years: Years in retirement
            risk_tolerance: "conservative", "moderate", or "aggressive"
            withdrawal_increase_rate: Annual increase in withdrawals (default 2% for inflation)
            include_inflation: Adjust returns for inflation

        Returns:
            MonteCarloResult with projection data including success rate
        """
        logger.info(f"Running {self.num_simulations} withdrawal simulations over {years} years")

        # Generate all returns upfront
        annual_returns = self.simulate_returns(years, risk_tolerance, include_inflation)

        # Initialize balance array
        balances = np.zeros((self.num_simulations, years + 1))
        balances[:, 0] = starting_balance

        # Track which simulations have failed (run out of money)
        failed = np.zeros(self.num_simulations, dtype=bool)
        yearly_success_rates = [1.0]

        for year in range(years):
            # Withdrawal increases each year
            year_withdrawal = annual_withdrawal * ((1 + withdrawal_increase_rate) ** year)

            # Apply withdrawal first, then returns
            balance_after_withdrawal = balances[:, year] - year_withdrawal

            # Mark any simulation that goes negative as failed
            newly_failed = (balance_after_withdrawal < 0) & ~failed
            failed = failed | (balance_after_withdrawal < 0)

            # Apply returns (failed simulations stay at 0)
            new_balance = np.where(
                balance_after_withdrawal > 0,
                balance_after_withdrawal * (1 + annual_returns[:, year]),
                0
            )
            balances[:, year + 1] = new_balance

            # Calculate success rate at this year
            success_rate = 1.0 - (np.sum(failed) / self.num_simulations)
            yearly_success_rates.append(success_rate)

        # Calculate percentiles
        percentiles = {
            10: np.percentile(balances, 10, axis=0).tolist(),
            25: np.percentile(balances, 25, axis=0).tolist(),
            50: np.percentile(balances, 50, axis=0).tolist(),
            75: np.percentile(balances, 75, axis=0).tolist(),
            90: np.percentile(balances, 90, axis=0).tolist(),
        }

        final_balances = balances[:, -1]
        overall_success_rate = 1.0 - (np.sum(failed) / self.num_simulations)

        return MonteCarloResult(
            percentiles=percentiles,
            success_rate=float(overall_success_rate),
            median_final_balance=float(np.median(final_balances)),
            mean_final_balance=float(np.mean(final_balances)),
            all_projections=balances,
            yearly_success_rates=yearly_success_rates,
            inflation_adjusted=include_inflation
        )

    def run_full_retirement_simulation(
        self,
        current_age: int,
        retirement_age: int,
        life_expectancy: int,
        current_savings: float,
        monthly_contribution: float,
        desired_annual_income: float,
        risk_tolerance: str = "moderate",
        contribution_increase_rate: float = 0.02,
        include_inflation: bool = True,
        social_security_annual: float = 0
    ) -> Dict:
        """
        Run complete retirement simulation including both accumulation and withdrawal phases

        Args:
            current_age: Current age
            retirement_age: Target retirement age
            life_expectancy: Expected age at death (default 90)
            current_savings: Current retirement savings
            monthly_contribution: Monthly contribution amount
            desired_annual_income: Desired annual retirement income
            risk_tolerance: Risk tolerance level
            contribution_increase_rate: Annual contribution increase
            include_inflation: Adjust for inflation
            social_security_annual: Expected annual Social Security income

        Returns:
            Dictionary with comprehensive simulation results
        """
        years_to_retirement = retirement_age - current_age
        years_in_retirement = life_expectancy - retirement_age

        # Phase 1: Accumulation
        accumulation_result = self.run_accumulation_simulation(
            current_savings=current_savings,
            monthly_contribution=monthly_contribution,
            years=years_to_retirement,
            risk_tolerance=risk_tolerance,
            contribution_increase_rate=contribution_increase_rate,
            include_inflation=include_inflation
        )

        # Net withdrawal needed (after Social Security)
        net_annual_withdrawal = max(0, desired_annual_income - social_security_annual)

        # Phase 2: Withdrawal (using median accumulated balance as starting point for display)
        # But actually run from each simulation's ending balance
        withdrawal_results = []

        # For efficiency, use the median balance for the main withdrawal simulation
        median_at_retirement = accumulation_result.median_final_balance

        # Run withdrawal phase with a slightly more conservative allocation
        withdrawal_risk = "conservative" if risk_tolerance == "conservative" else "moderate"

        withdrawal_result = self.run_withdrawal_simulation(
            starting_balance=median_at_retirement,
            annual_withdrawal=net_annual_withdrawal,
            years=years_in_retirement,
            risk_tolerance=withdrawal_risk,
            withdrawal_increase_rate=0.02,  # Increase withdrawals for inflation
            include_inflation=include_inflation
        )

        # Calculate the safe withdrawal rate
        safe_withdrawal_rate = (net_annual_withdrawal / median_at_retirement * 100) if median_at_retirement > 0 else 0

        # Determine if current plan is on track
        # Using 4% rule as benchmark
        required_savings = net_annual_withdrawal / 0.04 if net_annual_withdrawal > 0 else 0
        savings_gap = required_savings - median_at_retirement

        # Calculate suggested additional monthly savings to close gap
        if savings_gap > 0 and years_to_retirement > 0:
            # Simplified calculation for additional monthly savings needed
            mean_return, _ = self.get_portfolio_return_params(risk_tolerance)
            # Future value of annuity formula, solved for payment
            r = mean_return / 12  # Monthly rate
            n = years_to_retirement * 12  # Months
            if r > 0:
                additional_monthly = savings_gap * r / ((1 + r) ** n - 1)
            else:
                additional_monthly = savings_gap / n
        else:
            additional_monthly = 0

        return {
            "accumulation": {
                "years": years_to_retirement,
                "percentiles": accumulation_result.percentiles,
                "median_at_retirement": accumulation_result.median_final_balance,
                "mean_at_retirement": accumulation_result.mean_final_balance,
                "p10_at_retirement": accumulation_result.percentiles[10][-1],
                "p90_at_retirement": accumulation_result.percentiles[90][-1],
            },
            "withdrawal": {
                "years": years_in_retirement,
                "percentiles": withdrawal_result.percentiles,
                "success_rate": withdrawal_result.success_rate,
                "yearly_success_rates": withdrawal_result.yearly_success_rates,
                "median_final_balance": withdrawal_result.median_final_balance,
            },
            "analysis": {
                "current_age": current_age,
                "retirement_age": retirement_age,
                "life_expectancy": life_expectancy,
                "risk_tolerance": risk_tolerance,
                "inflation_adjusted": include_inflation,
                "num_simulations": self.num_simulations,
                "safe_withdrawal_rate": round(safe_withdrawal_rate, 2),
                "required_savings_4pct_rule": round(required_savings, 2),
                "projected_savings_median": round(median_at_retirement, 2),
                "savings_gap": round(max(0, savings_gap), 2),
                "additional_monthly_needed": round(max(0, additional_monthly), 2),
                "on_track": savings_gap <= 0 and withdrawal_result.success_rate >= 0.9,
                "success_probability": round(withdrawal_result.success_rate * 100, 1),
            },
            "projections": {
                # Combined timeline for charting
                "ages": list(range(current_age, life_expectancy + 1)),
                "p10": accumulation_result.percentiles[10] + withdrawal_result.percentiles[10][1:],
                "p25": accumulation_result.percentiles[25] + withdrawal_result.percentiles[25][1:],
                "p50": accumulation_result.percentiles[50] + withdrawal_result.percentiles[50][1:],
                "p75": accumulation_result.percentiles[75] + withdrawal_result.percentiles[75][1:],
                "p90": accumulation_result.percentiles[90] + withdrawal_result.percentiles[90][1:],
            }
        }


def run_monte_carlo_retirement(
    current_age: int,
    retirement_age: int,
    current_savings: float,
    monthly_contribution: float,
    desired_annual_income: float,
    risk_tolerance: str = "moderate",
    life_expectancy: int = 90,
    social_security_annual: float = 20000,
    num_simulations: int = 2000
) -> Dict:
    """
    Convenience function to run Monte Carlo retirement simulation

    Args:
        current_age: Current age
        retirement_age: Target retirement age
        current_savings: Current retirement savings
        monthly_contribution: Monthly contribution
        desired_annual_income: Desired annual income in retirement
        risk_tolerance: "conservative", "moderate", or "aggressive"
        life_expectancy: Expected lifespan (default 90)
        social_security_annual: Expected Social Security (default $20,000)
        num_simulations: Number of simulations (default 2,000)

    Returns:
        Complete simulation results dictionary
    """
    simulator = MonteCarloSimulator(num_simulations=num_simulations)
    return simulator.run_full_retirement_simulation(
        current_age=current_age,
        retirement_age=retirement_age,
        life_expectancy=life_expectancy,
        current_savings=current_savings,
        monthly_contribution=monthly_contribution,
        desired_annual_income=desired_annual_income,
        risk_tolerance=risk_tolerance,
        social_security_annual=social_security_annual
    )
