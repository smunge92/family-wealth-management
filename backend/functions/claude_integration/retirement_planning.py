"""
Claude Retirement Planning Endpoint
Provides AI-powered retirement projections with Monte Carlo simulation
"""

import azure.functions as func
import logging
import json
import os
from shared.claude_client import ClaudeClient
from shared.database import get_db_manager
from shared.monte_carlo import run_monte_carlo_retirement
from shared.auth import require_auth, get_cors_headers, validate_user_access
from shared.rate_limiter import rate_limit
from shared.validation import (
    validate_user_id, validate_integer, validate_float,
    validate_risk_tolerance, validate_request_body
)

logger = logging.getLogger(__name__)

bp = func.Blueprint()


@bp.route(route="insights/retirement", methods=["POST", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
@rate_limit(limit=5, window_seconds=60)  # 5 analyses per minute (heavy computation + Claude API)
async def plan_retirement(req: func.HttpRequest) -> func.HttpResponse:
    """
    Generate retirement planning recommendations using Monte Carlo simulation and Claude AI

    Expected request body:
    {
        "user_id": "string",
        "current_age": 35,
        "retirement_age": 65,
        "current_savings": 250000,
        "monthly_contribution": 2000,
        "desired_annual_income": 80000,
        "risk_tolerance": "moderate",  // "conservative", "moderate", "aggressive"
        "life_expectancy": 90,  // optional, default 90
        "social_security_annual": 20000  // optional, default 20000
    }
    """
    headers = get_cors_headers()

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    logger.info("Starting retirement planning analysis with Monte Carlo simulation")

    try:
        req_body = req.get_json()

        # Validate all inputs
        validation_schema = {
            "user_id": {"type": "user_id", "required": True},
            "current_age": {"type": "integer", "required": False, "min": 18, "max": 100},
            "retirement_age": {"type": "integer", "required": False, "min": 30, "max": 100},
            "life_expectancy": {"type": "integer", "required": False, "min": 50, "max": 120},
            "current_savings": {"type": "float", "required": False, "min": 0, "max": 100000000000},
            "monthly_contribution": {"type": "float", "required": False, "min": 0, "max": 1000000},
            "desired_annual_income": {"type": "float", "required": False, "min": 0, "max": 10000000},
            "social_security_annual": {"type": "float", "required": False, "min": 0, "max": 500000},
            "risk_tolerance": {"type": "risk_tolerance", "required": False}
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
        current_age = int(req_body.get("current_age", 35))
        retirement_age = int(req_body.get("retirement_age", 65))
        current_savings = float(req_body.get("current_savings", 0))
        monthly_contribution = float(req_body.get("monthly_contribution", 0))
        desired_annual_income = float(req_body.get("desired_annual_income", 60000))
        risk_tolerance = req_body.get("risk_tolerance", "moderate")
        life_expectancy = int(req_body.get("life_expectancy", 90))
        social_security_annual = float(req_body.get("social_security_annual", 20000))

        # Validate user has access to this user_id
        is_valid, error_response = validate_user_access(req, user_id)
        if not is_valid:
            return error_response

        # Validate inputs
        if current_age >= retirement_age:
            return func.HttpResponse(
                json.dumps({"error": "Current age must be less than retirement age"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        if retirement_age >= life_expectancy:
            return func.HttpResponse(
                json.dumps({"error": "Retirement age must be less than life expectancy"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        db = get_db_manager()

        # Get user's retirement accounts
        accounts = db.get_accounts_by_user(user_id)
        retirement_accounts = [a for a in accounts if a.get("account_type") in
                              ["401k", "ira", "roth_ira", "rrsp", "tfsa", "investment", "brokerage"]]

        # Run Monte Carlo simulation
        logger.info(f"Running Monte Carlo simulation with 10,000 iterations")
        monte_carlo_results = run_monte_carlo_retirement(
            current_age=current_age,
            retirement_age=retirement_age,
            current_savings=current_savings,
            monthly_contribution=monthly_contribution,
            desired_annual_income=desired_annual_income,
            risk_tolerance=risk_tolerance,
            life_expectancy=life_expectancy,
            social_security_annual=social_security_annual,
            num_simulations=10000
        )

        # Build comprehensive retirement prompt with Monte Carlo results
        analysis_data = monte_carlo_results["analysis"]
        prompt = f"""
You are an expert retirement financial planner. Based on the Monte Carlo simulation results below, provide personalized recommendations.

**User Profile:**
- Current Age: {current_age}
- Target Retirement Age: {retirement_age}
- Life Expectancy: {life_expectancy}
- Years Until Retirement: {retirement_age - current_age}
- Current Retirement Savings: ${current_savings:,.2f}
- Monthly Contribution: ${monthly_contribution:,.2f}
- Desired Annual Retirement Income: ${desired_annual_income:,.2f}
- Expected Social Security: ${social_security_annual:,.2f}/year
- Risk Tolerance: {risk_tolerance}

**Monte Carlo Simulation Results (10,000 simulations):**
- Median Projected Savings at Retirement: ${analysis_data['projected_savings_median']:,.2f}
- 10th Percentile (pessimistic): ${monte_carlo_results['accumulation']['p10_at_retirement']:,.2f}
- 90th Percentile (optimistic): ${monte_carlo_results['accumulation']['p90_at_retirement']:,.2f}
- Probability of Not Running Out of Money: {analysis_data['success_probability']}%
- Required Savings (4% rule): ${analysis_data['required_savings_4pct_rule']:,.2f}
- Savings Gap: ${analysis_data['savings_gap']:,.2f}
- On Track: {"Yes" if analysis_data['on_track'] else "No"}
- Safe Withdrawal Rate: {analysis_data['safe_withdrawal_rate']}%

**Connected Retirement Accounts:**
{json.dumps([{"name": a.get("account_name"), "type": a.get("account_type")} for a in retirement_accounts], indent=2)}

Based on these Monte Carlo simulation results, please provide:

## 1. Probability Assessment
Interpret the simulation results - what does a {analysis_data['success_probability']}% success rate mean? Is this acceptable?

## 2. Scenario Analysis
- Best case scenario (90th percentile): What could happen if markets outperform?
- Expected case (50th percentile): Most likely outcome
- Worst case (10th percentile): What to prepare for if markets underperform

## 3. Risk Assessment
Based on the simulation spread, assess the level of uncertainty and what factors most impact the outcomes.

## 4. Recommendations
{"The user is currently ON TRACK for retirement." if analysis_data['on_track'] else f"The user has a savings gap of ${analysis_data['savings_gap']:,.2f}. Additional monthly savings of ${analysis_data['additional_monthly_needed']:,.2f} would be needed to close this gap."}

Provide 5-7 specific, actionable recommendations to improve retirement outcomes.

## 5. Sensitivity Analysis
What changes (contributions, retirement age, spending) would most improve the success probability?

Format your response with clear headers, bullet points, and specific dollar amounts.
"""

        claude = ClaudeClient()
        response = claude.client.messages.create(
            model=claude.model,
            max_tokens=claude.max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        ai_analysis = response.content[0].text

        # Save insight
        save_insight(db, user_id, "retirement", ai_analysis)

        logger.info(f"Retirement planning completed for user {user_id}")

        # Prepare projection data for charts (subsample for performance)
        projections = monte_carlo_results["projections"]
        ages = projections["ages"]

        # Create yearly projection data
        projection_data = []
        for i, age in enumerate(ages):
            projection_data.append({
                "age": age,
                "p10": round(projections["p10"][i], 2),
                "p25": round(projections["p25"][i], 2),
                "p50": round(projections["p50"][i], 2),
                "p75": round(projections["p75"][i], 2),
                "p90": round(projections["p90"][i], 2),
            })

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "insight_type": "retirement",
                "analysis": ai_analysis,
                "monte_carlo": {
                    "num_simulations": 10000,
                    "success_probability": analysis_data["success_probability"],
                    "on_track": analysis_data["on_track"],
                    "savings_gap": analysis_data["savings_gap"],
                    "additional_monthly_needed": analysis_data["additional_monthly_needed"],
                    "safe_withdrawal_rate": analysis_data["safe_withdrawal_rate"],
                    "accumulation": {
                        "median_at_retirement": monte_carlo_results["accumulation"]["median_at_retirement"],
                        "p10_at_retirement": monte_carlo_results["accumulation"]["p10_at_retirement"],
                        "p90_at_retirement": monte_carlo_results["accumulation"]["p90_at_retirement"],
                    },
                    "withdrawal": {
                        "success_rate": monte_carlo_results["withdrawal"]["success_rate"],
                        "yearly_success_rates": monte_carlo_results["withdrawal"]["yearly_success_rates"],
                    }
                },
                "projections": projection_data,
                "summary": {
                    "current_age": current_age,
                    "retirement_age": retirement_age,
                    "life_expectancy": life_expectancy,
                    "current_savings": current_savings,
                    "monthly_contribution": monthly_contribution,
                    "desired_annual_income": desired_annual_income,
                    "social_security_annual": social_security_annual,
                    "risk_tolerance": risk_tolerance,
                    "projected_at_retirement_median": round(monte_carlo_results["accumulation"]["median_at_retirement"], 2),
                    "projected_at_retirement_p10": round(monte_carlo_results["accumulation"]["p10_at_retirement"], 2),
                    "projected_at_retirement_p90": round(monte_carlo_results["accumulation"]["p90_at_retirement"], 2),
                    "success_probability": analysis_data["success_probability"]
                }
            }),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        logger.error(f"Error planning retirement: {str(e)}")
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
