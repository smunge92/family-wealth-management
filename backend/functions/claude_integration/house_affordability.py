"""
Claude House Affordability Endpoint
Provides AI-powered home buying analysis
"""

import azure.functions as func
import logging
import json
import os
from shared.claude_client import ClaudeClient
from shared.database import get_db_manager
from shared.auth import require_auth, get_cors_headers, validate_user_access
from shared.rate_limiter import rate_limit
from shared.validation import validate_request_body, validate_string

logger = logging.getLogger(__name__)

bp = func.Blueprint()


@bp.route(route="insights/house", methods=["POST", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
@rate_limit(limit=10, window_seconds=60)  # 10 analyses per minute (calls Claude API)
async def analyze_house_affordability(req: func.HttpRequest) -> func.HttpResponse:
    """
    Analyze house buying affordability using Claude AI

    Expected request body:
    {
        "user_id": "string",
        "annual_income": 150000,
        "current_savings": 100000,
        "monthly_debts": 500,
        "target_location": "Seattle, WA",
        "down_payment_percent": 20
    }
    """
    headers = get_cors_headers()

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    logger.info("Starting house affordability analysis")

    try:
        req_body = req.get_json()
        logger.info(f"Received request body keys: {list(req_body.keys()) if req_body else 'None'}")

        # Validate all inputs
        validation_schema = {
            "user_id": {"type": "user_id", "required": True},
            "annual_income": {"type": "float", "required": False, "min": 0, "max": 100000000},
            "current_savings": {"type": "float", "required": False, "min": 0, "max": 100000000000},
            "monthly_debts": {"type": "float", "required": False, "min": 0, "max": 10000000},
            "down_payment_percent": {"type": "float", "required": False, "min": 1, "max": 99},
            "target_location": {"type": "string", "required": False, "max_length": 200}
        }

        is_valid, error_msg = validate_request_body(req_body, validation_schema)
        if not is_valid:
            return func.HttpResponse(
                json.dumps({"error": error_msg}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        user_id = req_body.get("user_id")
        annual_income = float(req_body.get("annual_income") or 100000)
        current_savings = float(req_body.get("current_savings") or 50000)
        monthly_debts = float(req_body.get("monthly_debts") or 0)
        target_location = req_body.get("target_location", "US Average")
        down_payment_percent = float(req_body.get("down_payment_percent") or 20)

        logger.info(f"Parsed values - annual_income: {annual_income}, current_savings: {current_savings}, monthly_debts: {monthly_debts}, down_payment_percent: {down_payment_percent}")

        # Ensure minimum valid values to prevent 0 calculations
        if annual_income <= 0:
            annual_income = 100000.0
            logger.warning(f"annual_income was invalid, defaulting to {annual_income}")
        if down_payment_percent <= 0 or down_payment_percent >= 100:
            down_payment_percent = 20.0
            logger.warning(f"down_payment_percent was invalid, defaulting to {down_payment_percent}")

        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id is required"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate user has access to this user_id
        is_valid, error_response = validate_user_access(req, user_id)
        if not is_valid:
            return error_response

        db = get_db_manager()
        accounts = db.get_accounts_by_user(user_id)

        # Calculate basic affordability metrics
        monthly_income = float(annual_income) / 12.0
        max_housing_payment = monthly_income * 0.28  # 28% rule for housing
        max_total_debt = monthly_income * 0.36  # 36% rule for total debt
        available_for_housing = max_total_debt - float(monthly_debts)

        # Use the more conservative of the two, but ensure it's not negative
        max_monthly_payment = max(0.0, min(max_housing_payment, available_for_housing))

        logger.info(f"Step 1 - monthly_income: {monthly_income}, max_housing_payment: {max_housing_payment}, available_for_housing: {available_for_housing}, max_monthly_payment: {max_monthly_payment}")

        # Estimate max home price (assuming 30-year mortgage at 7% interest)
        interest_rate = 0.07 / 12.0
        num_payments = 360

        # Calculate max loan using mortgage formula: P = M * [(1-(1+r)^-n)/r]
        if max_monthly_payment > 0:
            factor = (1.0 - pow(1.0 + interest_rate, -num_payments)) / interest_rate
            max_loan = max_monthly_payment * factor
            logger.info(f"Step 2 - factor: {factor}, max_loan: {max_loan}")
        else:
            max_loan = 0.0
            logger.warning("max_monthly_payment is 0, so max_loan is 0")

        # Calculate max home price based on down payment percentage
        down_payment_fraction = float(down_payment_percent) / 100.0
        if down_payment_fraction < 1.0:
            max_home_price = max_loan / (1.0 - down_payment_fraction)
        else:
            max_home_price = max_loan  # 100% down payment

        required_down_payment = max_home_price * down_payment_fraction

        logger.info(f"Step 3 - down_payment_fraction: {down_payment_fraction}, max_home_price: {max_home_price}, required_down_payment: {required_down_payment}")

        # Final summary log
        logger.info(f"FINAL VALUES - max_monthly_payment: {max_monthly_payment}, max_home_price: {max_home_price}")

        # Build prompt
        prompt = f"""
You are an expert real estate financial advisor. Provide a comprehensive home buying affordability analysis.

**Financial Profile:**
- Annual Household Income: ${annual_income:,.2f}
- Monthly Income: ${monthly_income:,.2f}
- Current Savings: ${current_savings:,.2f}
- Monthly Debt Payments: ${monthly_debts:,.2f}
- Target Location: {target_location}
- Desired Down Payment: {down_payment_percent}%

**Connected Accounts:**
{json.dumps([{"name": a.get("account_name"), "type": a.get("account_type")} for a in accounts], indent=2)}

**Calculated Metrics (28/36 Rule):**
- Maximum Monthly Housing Payment: ${max_monthly_payment:,.2f}
- Maximum Home Price: ${max_home_price:,.2f}
- Required Down Payment: ${required_down_payment:,.2f}

Please provide:

## 1. Affordability Summary
- Maximum affordable home price
- Recommended price range (conservative to stretch)
- Down payment readiness assessment

## 2. Monthly Cost Breakdown
For a home at the maximum affordable price, estimate:
- Mortgage payment (P&I)
- Property taxes (estimate for {target_location})
- Home insurance
- PMI (if applicable)
- HOA (typical for area)
- Total monthly housing cost

## 3. Upfront Costs
- Down payment amount
- Closing costs (estimate 2-5%)
- Moving expenses
- Emergency fund for home repairs
- Total cash needed

## 4. Location Analysis
For {target_location}:
- Typical home prices in the area
- Market conditions (buyer's/seller's market)
- Neighborhoods to consider at this budget
- Commute and lifestyle factors

## 5. Timeline & Action Plan
- Are they ready to buy now?
- If not, what's the timeline?
- Savings goals to meet
- Credit score recommendations
- Pre-approval steps

## 6. Specific Recommendations
Provide 5-7 actionable next steps

Format with clear headers and bullet points.
"""

        claude = ClaudeClient()
        response = claude.client.messages.create(
            model=claude.model,
            max_tokens=claude.max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        analysis = response.content[0].text

        # Calculate savings timeline data for charts
        savings_timeline = []
        monthly_savings_rate = monthly_income * 0.20  # Assume 20% savings rate
        savings = current_savings
        for month in range(37):  # 3 years
            savings_timeline.append({
                "month": month,
                "savings": round(savings, 2),
                "target": round(required_down_payment + 15000, 2)  # Down payment + closing
            })
            savings += monthly_savings_rate

        # Save insight
        save_insight(db, user_id, "house", analysis)

        logger.info(f"House affordability analysis completed for user {user_id}")

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "insight_type": "house",
                "analysis": analysis,
                "calculations": {
                    "max_home_price": round(max_home_price, 2),
                    "max_monthly_payment": round(max_monthly_payment, 2),
                    "required_down_payment": round(required_down_payment, 2),
                    "current_savings": current_savings,
                    "savings_gap": round(max(0, required_down_payment + 15000 - current_savings), 2),
                    "ready_to_buy": current_savings >= (required_down_payment + 15000)
                },
                "savings_timeline": savings_timeline,
                "debug": {
                    "inputs": {
                        "annual_income": annual_income,
                        "current_savings": current_savings,
                        "monthly_debts": monthly_debts,
                        "down_payment_percent": down_payment_percent
                    },
                    "intermediates": {
                        "monthly_income": round(monthly_income, 2),
                        "max_housing_payment": round(max_housing_payment, 2),
                        "max_total_debt": round(max_total_debt, 2),
                        "available_for_housing": round(available_for_housing, 2),
                        "max_monthly_payment": round(max_monthly_payment, 2),
                        "max_loan": round(max_loan, 2),
                        "down_payment_fraction": down_payment_fraction
                    }
                }
            }),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        logger.error(f"Error analyzing house affordability: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "An error occurred. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )


def save_insight(db, user_id: str, insight_type: str, response: str):
    """Save AI insight to database"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_insights (user_id, insight_type, response, created_at)
                VALUES (%s, %s, %s, GETUTCDATE())
            """, (user_id, insight_type, response[:4000]))
            conn.commit()
    except Exception as e:
        logger.warning(f"Failed to save insight: {e}")
