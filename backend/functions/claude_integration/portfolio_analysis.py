"""
Claude Portfolio Analysis Endpoint
Provides AI-powered portfolio insights
"""

import azure.functions as func
import logging
import json
import os
from shared.claude_client import ClaudeClient
from shared.database import get_db_manager
from shared.auth import require_auth, get_cors_headers, validate_user_access
from shared.rate_limiter import rate_limit
from shared.validation import validate_user_id, validate_integer

logger = logging.getLogger(__name__)

bp = func.Blueprint()


@bp.route(route="insights/portfolio", methods=["POST", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
@rate_limit(limit=10, window_seconds=60)  # 10 analyses per minute (calls Claude API)
async def analyze_portfolio(req: func.HttpRequest) -> func.HttpResponse:
    """
    Analyze user's portfolio using Claude AI

    Expected request body:
    {
        "user_id": "string",
        "family_member_id": int (optional)
    }
    """
    headers = get_cors_headers()

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    logger.info("Starting portfolio analysis")

    try:
        req_body = req.get_json()
        user_id = req_body.get("user_id")
        family_member_id = req_body.get("family_member_id")

        # Validate user_id
        is_valid, error_msg = validate_user_id(user_id)
        if not is_valid:
            return func.HttpResponse(
                json.dumps({"error": error_msg}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate family_member_id if provided
        if family_member_id is not None:
            is_valid, error_msg = validate_integer(family_member_id, "family_member_id", required=False, min_value=1)
            if not is_valid:
                return func.HttpResponse(
                    json.dumps({"error": error_msg}),
                    status_code=400,
                    mimetype="application/json",
                    headers=headers
                )

        # Validate user has access to this user_id
        is_valid, error_response = validate_user_access(req, user_id)
        if not is_valid:
            return error_response

        db = get_db_manager()

        # Get user's accounts (optionally filtered by family member)
        accounts = db.get_accounts_by_user(user_id, family_member_id=family_member_id)
        if not accounts:
            return func.HttpResponse(
                json.dumps({"error": "No accounts found. Please connect accounts first."}),
                status_code=404,
                mimetype="application/json",
                headers=headers
            )

        # Get recent transactions (optionally filtered by family member)
        transactions = db.get_transactions_by_user(user_id, limit=100, family_member_id=family_member_id)

        # Get current balances from database
        account_ids = [a.get("account_id") for a in accounts]
        balance_data = db.get_latest_balances_for_accounts(account_ids)

        # Build balances list for AI analysis
        balances = []
        for account in accounts:
            account_id = account.get("account_id")
            balance_info = balance_data.get(account_id, {})
            balances.append({
                "account_name": account.get("account_name"),
                "account_type": account.get("account_type"),
                "currency": account.get("currency", "USD"),
                "current_balance": balance_info.get("current_balance", 0)
            })

        # Prepare data for Claude (remove sensitive info)
        accounts_data = [{
            "name": a.get("account_name"),
            "type": a.get("account_type"),
            "currency": a.get("currency", "USD")
        } for a in accounts]

        # Build chart_data and table_data for frontend visualization
        chart_data, table_data = build_portfolio_chart_data(accounts, balance_data)

        transactions_data = [{
            "date": str(t.get("date")),
            "amount": float(t.get("amount", 0)),
            "description": t.get("description"),
            "category": t.get("category"),
            "account_type": t.get("account_type")
        } for t in transactions]

        # Call Claude for analysis
        claude = ClaudeClient()
        analysis = claude.analyze_portfolio(accounts_data, transactions_data, balances)

        # Save insight to database
        save_insight(db, user_id, "portfolio", analysis)

        logger.info(f"Portfolio analysis completed for user {user_id}")

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "insight_type": "portfolio",
                "analysis": analysis,
                "accounts_analyzed": len(accounts),
                "transactions_analyzed": len(transactions),
                "chart_data": chart_data,
                "table_data": table_data
            }),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        logger.error(f"Error analyzing portfolio: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "An error occurred. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )


def build_portfolio_chart_data(accounts: list, balance_data: dict) -> tuple:
    """
    Build structured chart_data and table_data for portfolio visualization.
    Returns (chart_data, table_data) tuple.
    """
    # Aggregate balances by account type
    by_account_type = {}
    total_assets = 0
    total_liabilities = 0
    accounts_table = []

    for account in accounts:
        account_id = account.get("account_id")
        account_type = account.get("account_type", "other")
        account_name = account.get("account_name", "Unknown")
        balance_info = balance_data.get(account_id, {})
        current_balance = balance_info.get("current_balance", 0)

        # Add to table data
        accounts_table.append({
            "name": account_name,
            "type": account_type,
            "balance": current_balance,
            "institution": account.get("institution_name", "Unknown")
        })

        # Aggregate by type
        if account_type not in by_account_type:
            by_account_type[account_type] = 0
        by_account_type[account_type] += current_balance

        # Calculate totals (credit cards and loans are liabilities)
        if account_type in ["credit", "loan"]:
            total_liabilities += abs(current_balance)
        else:
            total_assets += current_balance

    # Convert to chart format
    type_chart_data = [
        {"name": _format_account_type(atype), "value": round(value, 2)}
        for atype, value in by_account_type.items()
        if value != 0  # Exclude zero balances
    ]

    # Sort by absolute value descending
    type_chart_data.sort(key=lambda x: abs(x["value"]), reverse=True)

    chart_data = {
        "by_account_type": type_chart_data,
        "total_assets": round(total_assets, 2),
        "total_liabilities": round(total_liabilities, 2),
        "net_worth": round(total_assets - total_liabilities, 2)
    }

    table_data = {
        "accounts": accounts_table
    }

    return chart_data, table_data


def _format_account_type(account_type: str) -> str:
    """Format account type for display"""
    type_map = {
        "depository": "Checking/Savings",
        "investment": "Investment",
        "credit": "Credit Cards",
        "loan": "Loans",
        "brokerage": "Brokerage",
        "other": "Other"
    }
    return type_map.get(account_type, account_type.title())


@bp.route(route="insights/spending", methods=["POST", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
@rate_limit(limit=10, window_seconds=60)  # 10 analyses per minute (calls Claude API)
async def analyze_spending(req: func.HttpRequest) -> func.HttpResponse:
    """
    Analyze spending patterns using Claude AI

    Expected request body:
    {
        "user_id": "string",
        "family_member_id": int (optional)
    }
    """
    headers = get_cors_headers()

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    logger.info("Starting spending analysis")

    try:
        req_body = req.get_json()
        user_id = req_body.get("user_id")
        family_member_id = req_body.get("family_member_id")

        # Validate user_id
        is_valid, error_msg = validate_user_id(user_id)
        if not is_valid:
            return func.HttpResponse(
                json.dumps({"error": error_msg}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate family_member_id if provided
        if family_member_id is not None:
            is_valid, error_msg = validate_integer(family_member_id, "family_member_id", required=False, min_value=1)
            if not is_valid:
                return func.HttpResponse(
                    json.dumps({"error": error_msg}),
                    status_code=400,
                    mimetype="application/json",
                    headers=headers
                )

        # Validate user has access to this user_id
        is_valid, error_response = validate_user_access(req, user_id)
        if not is_valid:
            return error_response

        db = get_db_manager()

        # Get transactions (optionally filtered by family member)
        transactions = db.get_transactions_by_user(user_id, limit=200, family_member_id=family_member_id)

        if not transactions:
            return func.HttpResponse(
                json.dumps({"error": "No transactions found. Please sync transactions first."}),
                status_code=404,
                mimetype="application/json",
                headers=headers
            )

        # Prepare transactions for analysis
        transactions_data = [{
            "date": str(t.get("date")),
            "amount": float(t.get("amount", 0)),
            "description": t.get("description"),
            "category": t.get("category")
        } for t in transactions]

        # Build chart_data and table_data for frontend visualization
        chart_data, table_data = build_spending_chart_data(transactions)

        # Build spending analysis prompt
        prompt = f"""
You are a personal finance expert. Analyze these transactions and provide:

1. **Spending Categories Breakdown** - List top spending categories with amounts
2. **Monthly Spending Trend** - Average monthly spending
3. **Top Merchants** - Where most money is being spent
4. **Savings Opportunities** - Areas to cut back
5. **Unusual Transactions** - Any outliers or suspicious patterns
6. **Budget Recommendations** - Suggested monthly budget by category

Transactions (last 200):
{json.dumps(transactions_data, indent=2)}

Provide actionable insights in a clear, structured format with bullet points.
"""

        claude = ClaudeClient()
        response = claude.client.messages.create(
            model=claude.model,
            max_tokens=claude.max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        analysis = response.content[0].text

        save_insight(db, user_id, "spending", analysis)

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "insight_type": "spending",
                "analysis": analysis,
                "transactions_analyzed": len(transactions),
                "chart_data": chart_data,
                "table_data": table_data
            }),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        logger.error(f"Error analyzing spending: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "An error occurred. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )


def build_spending_chart_data(transactions: list) -> tuple:
    """
    Build structured chart_data and table_data for spending visualization.
    Returns (chart_data, table_data) tuple.
    """
    from collections import defaultdict
    from datetime import datetime

    # Initialize aggregations
    by_category = defaultdict(float)
    by_month = defaultdict(lambda: {"expenses": 0, "income": 0})
    by_merchant = defaultdict(lambda: {"amount": 0, "count": 0})
    total_expenses = 0
    total_income = 0

    for txn in transactions:
        amount = float(txn.get("amount", 0))
        category = txn.get("category") or "Uncategorized"
        description = txn.get("description") or "Unknown"
        date_str = str(txn.get("date", ""))

        # Parse month from date
        try:
            if date_str:
                date_obj = datetime.strptime(date_str[:10], "%Y-%m-%d")
                month_key = date_obj.strftime("%b '%y")  # e.g., "Oct '24"
            else:
                month_key = "Unknown"
        except (ValueError, TypeError):
            month_key = "Unknown"

        # In Plaid, positive = expense, negative = income
        if amount > 0:
            # Expense
            by_category[category] += amount
            by_month[month_key]["expenses"] += amount
            total_expenses += amount

            # Track merchant (use first word of description as merchant name)
            merchant = description.split()[0] if description else "Unknown"
            by_merchant[merchant]["amount"] += amount
            by_merchant[merchant]["count"] += 1
        else:
            # Income
            by_month[month_key]["income"] += abs(amount)
            total_income += abs(amount)

    # Build category chart data (top 8 categories)
    category_chart = [
        {"name": cat, "value": round(val, 2)}
        for cat, val in sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:8]
    ]

    # Build monthly trend data (sorted by date)
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    def month_sort_key(item):
        try:
            month_str = item[0][:3]
            year_str = item[0][-2:]
            month_idx = month_order.index(month_str) if month_str in month_order else 0
            return (int(year_str), month_idx)
        except (ValueError, IndexError):
            return (0, 0)

    monthly_trend = [
        {"month": month, "expenses": round(data["expenses"], 2), "income": round(data["income"], 2)}
        for month, data in sorted(by_month.items(), key=month_sort_key)
        if month != "Unknown"
    ][-6:]  # Last 6 months

    # Build top merchants data
    top_merchants = [
        {"name": merchant, "amount": round(data["amount"], 2), "count": data["count"]}
        for merchant, data in sorted(by_merchant.items(), key=lambda x: x[1]["amount"], reverse=True)[:10]
    ]

    # Build category breakdown table
    total_cat_amount = sum(by_category.values()) or 1  # Avoid division by zero
    category_breakdown = [
        {
            "category": cat,
            "amount": round(val, 2),
            "percentage": round((val / total_cat_amount) * 100, 1)
        }
        for cat, val in sorted(by_category.items(), key=lambda x: x[1], reverse=True)
    ]

    chart_data = {
        "by_category": category_chart,
        "monthly_trend": monthly_trend,
        "top_merchants": top_merchants,
        "summary": {
            "total_expenses": round(total_expenses, 2),
            "total_income": round(total_income, 2)
        }
    }

    table_data = {
        "category_breakdown": category_breakdown
    }

    return chart_data, table_data


def save_insight(db, user_id: str, insight_type: str, response: str):
    """Save AI insight to database"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_insights (user_id, insight_type, response, created_at)
                VALUES (%s, %s, %s, GETUTCDATE())
            """, (user_id, insight_type, response[:4000]))  # Truncate if too long
            conn.commit()
    except Exception as e:
        logger.warning(f"Failed to save insight: {e}")
