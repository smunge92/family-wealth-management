"""
Claude API client wrapper for AI/ML features
"""

import os
import logging
from typing import Dict, List, Optional, AsyncIterator
from anthropic import Anthropic, AsyncAnthropic
import json

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Wrapper for Claude API operations"""

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        self.client = Anthropic(api_key=self.api_key)
        self.async_client = AsyncAnthropic(api_key=self.api_key)
        self.max_tokens = 4096

    def analyze_portfolio(
        self,
        accounts_data: List[Dict],
        transactions_data: List[Dict],
        balances_data: List[Dict]
    ) -> str:
        """
        Analyze portfolio using Claude

        Args:
            accounts_data: List of account details
            transactions_data: List of recent transactions
            balances_data: List of account balances

        Returns:
            Portfolio analysis text
        """
        prompt = self._build_portfolio_prompt(accounts_data, transactions_data, balances_data)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Error analyzing portfolio: {str(e)}")
            raise

    def plan_retirement(
        self,
        current_age: int,
        retirement_age: int,
        current_savings: float,
        monthly_contribution: float,
        accounts_data: List[Dict]
    ) -> str:
        """
        Generate retirement planning recommendations

        Args:
            current_age: User's current age
            retirement_age: Target retirement age
            current_savings: Total current retirement savings
            monthly_contribution: Monthly contribution amount
            accounts_data: List of retirement accounts

        Returns:
            Retirement planning analysis
        """
        prompt = self._build_retirement_prompt(
            current_age, retirement_age, current_savings,
            monthly_contribution, accounts_data
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Error planning retirement: {str(e)}")
            raise

    def analyze_house_affordability(
        self,
        annual_income: float,
        current_savings: float,
        monthly_debts: float,
        target_location: str,
        accounts_data: List[Dict]
    ) -> str:
        """
        Analyze house buying affordability

        Args:
            annual_income: Combined annual income
            current_savings: Available savings for down payment
            monthly_debts: Total monthly debt obligations
            target_location: Target city/area
            accounts_data: Account details

        Returns:
            House affordability analysis
        """
        prompt = self._build_house_affordability_prompt(
            annual_income, current_savings, monthly_debts,
            target_location, accounts_data
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Error analyzing house affordability: {str(e)}")
            raise

    def plan_family_costs(
        self,
        num_children: int,
        children_ages: List[int],
        location: str,
        annual_income: float
    ) -> str:
        """
        Project family planning costs

        Args:
            num_children: Number of children (planned or existing)
            children_ages: Ages of children
            location: Location (affects costs)
            annual_income: Annual household income

        Returns:
            Family planning cost analysis
        """
        prompt = self._build_family_planning_prompt(
            num_children, children_ages, location, annual_income
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Error planning family costs: {str(e)}")
            raise

    def categorize_transactions(
        self,
        transactions: List[Dict]
    ) -> List[Dict]:
        """
        Use Claude to intelligently categorize transactions

        Args:
            transactions: List of transactions to categorize

        Returns:
            List of transactions with categories
        """
        prompt = self._build_categorization_prompt(transactions)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Parse JSON response
            categorized = json.loads(response.content[0].text)
            return categorized

        except Exception as e:
            logger.error(f"Error categorizing transactions: {str(e)}")
            raise

    async def stream_analysis(
        self,
        prompt: str
    ) -> AsyncIterator[str]:
        """
        Stream analysis response from Claude

        Args:
            prompt: Analysis prompt

        Yields:
            Text chunks from Claude's response
        """
        try:
            async with self.async_client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Error streaming analysis: {str(e)}")
            raise

    def _build_portfolio_prompt(
        self,
        accounts_data: List[Dict],
        transactions_data: List[Dict],
        balances_data: List[Dict]
    ) -> str:
        """Build prompt for portfolio analysis"""
        return f"""
You are a financial advisor analyzing a family's portfolio. Provide a comprehensive analysis including:

1. Asset Allocation Assessment
2. Diversification Analysis
3. Risk Profile
4. Recommendations for Improvement

Accounts:
{json.dumps(accounts_data, indent=2)}

Recent Transactions (last 30 days):
{json.dumps(transactions_data[:100], indent=2)}

Current Balances:
{json.dumps(balances_data, indent=2)}

Provide actionable insights and recommendations.
"""

    def _build_retirement_prompt(
        self,
        current_age: int,
        retirement_age: int,
        current_savings: float,
        monthly_contribution: float,
        accounts_data: List[Dict]
    ) -> str:
        """Build prompt for retirement planning"""
        return f"""
You are a retirement planning expert. Analyze this scenario and provide detailed recommendations:

Current Age: {current_age}
Retirement Age: {retirement_age}
Current Retirement Savings: ${current_savings:,.2f}
Monthly Contribution: ${monthly_contribution:,.2f}

Retirement Accounts:
{json.dumps(accounts_data, indent=2)}

Provide:
1. Projected retirement savings at target age (assuming 7% annual return)
2. Monthly retirement income projection
3. Contribution recommendations
4. Account optimization strategies (401k, IRA, RRSP, etc.)
5. Tax optimization strategies
"""

    def _build_house_affordability_prompt(
        self,
        annual_income: float,
        current_savings: float,
        monthly_debts: float,
        target_location: str,
        accounts_data: List[Dict]
    ) -> str:
        """Build prompt for house affordability analysis"""
        return f"""
You are a real estate financial advisor. Analyze house buying affordability:

Annual Income: ${annual_income:,.2f}
Available Savings: ${current_savings:,.2f}
Monthly Debts: ${monthly_debts:,.2f}
Target Location: {target_location}

Accounts:
{json.dumps(accounts_data, indent=2)}

Provide:
1. Maximum affordable house price (28/36 rule)
2. Recommended down payment amount
3. Estimated monthly mortgage payment
4. Total upfront costs (closing, moving, etc.)
5. Timeline to readiness if not ready now
6. Specific recommendations for the target location
"""

    def _build_family_planning_prompt(
        self,
        num_children: int,
        children_ages: List[int],
        location: str,
        annual_income: float
    ) -> str:
        """Build prompt for family planning"""
        return f"""
You are a family financial planning expert. Analyze costs for:

Number of Children: {num_children}
Children Ages: {children_ages}
Location: {location}
Annual Income: ${annual_income:,.2f}

Provide detailed cost projections for:
1. Childcare costs (daycare, after-school care)
2. Education costs (K-12, college/university)
3. Healthcare costs (insurance, out-of-pocket)
4. 529/RESP education savings recommendations
5. Life insurance and disability insurance needs
6. Budget impact analysis
"""

    def _build_categorization_prompt(self, transactions: List[Dict]) -> str:
        """Build prompt for transaction categorization"""
        return f"""
Categorize these transactions into standard categories (groceries, dining, transportation, utilities, healthcare, entertainment, shopping, etc.).

Return a JSON array with each transaction having an added "category" field.

Transactions:
{json.dumps(transactions, indent=2)}
"""


# Global Claude client instance
claude_client = ClaudeClient()
