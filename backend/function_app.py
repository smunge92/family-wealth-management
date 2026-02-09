"""
Family Wealth Management - Azure Functions App
Main entry point for all Azure Functions using v2 programming model
"""

import azure.functions as func
import logging

# Configure centralized logging with Application Insights
from shared.logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize the function app
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Import and register blueprints
from functions.plaid_integration.connect_account import bp as plaid_connect_bp
from functions.plaid_integration.sync_transactions import bp as plaid_sync_bp
from functions.plaid_integration.historical_data import bp as plaid_history_bp
from functions.plaid_integration.csv_import import bp as csv_import_bp
from functions.plaid_integration.webhooks import bp as webhooks_bp

from functions.claude_integration.portfolio_analysis import bp as portfolio_bp
from functions.claude_integration.retirement_planning import bp as retirement_bp
from functions.claude_integration.house_affordability import bp as house_bp
from functions.claude_integration.family_planning import bp as family_bp

from functions.data_aggregation.aggregate_balances import bp as balances_bp
from functions.data_aggregation.calculate_networth import bp as networth_bp
from functions.data_aggregation.tax_integration import bp as tax_bp

from functions.scheduled_jobs.daily_sync import bp as daily_bp
from functions.scheduled_jobs.weekly_analysis import bp as weekly_bp

from functions.api.accounts import bp as accounts_api_bp
from functions.api.transactions import bp as transactions_api_bp
from functions.api.insights import bp as insights_api_bp
from functions.api.family_members import bp as family_members_api_bp
from functions.api.categories import bp as categories_api_bp

# Register all blueprints
app.register_functions(plaid_connect_bp)
app.register_functions(plaid_sync_bp)
app.register_functions(plaid_history_bp)
app.register_functions(csv_import_bp)
app.register_functions(webhooks_bp)

app.register_functions(portfolio_bp)
app.register_functions(retirement_bp)
app.register_functions(house_bp)
app.register_functions(family_bp)

app.register_functions(balances_bp)
app.register_functions(networth_bp)
app.register_functions(tax_bp)

app.register_functions(daily_bp)
app.register_functions(weekly_bp)

app.register_functions(accounts_api_bp)
app.register_functions(transactions_api_bp)
app.register_functions(insights_api_bp)
app.register_functions(family_members_api_bp)
app.register_functions(categories_api_bp)

logger.info("Family Wealth Management Function App initialized with all blueprints")
