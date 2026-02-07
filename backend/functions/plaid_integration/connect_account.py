"""
Plaid Connect Account Functions
Handles Link token creation, public token exchange, and account management
"""

import azure.functions as func
import logging
import json
import os
from shared.plaid_client import PlaidClient
from shared.database import get_db_manager
from shared.auth import require_auth, get_cors_headers, validate_user_access, get_user_from_request
from shared.rate_limiter import rate_limit
from shared.validation import validate_user_id, validate_email, validate_string, validate_plaid_token
from shared.audit import audit_log, audit_access, AuditAction

logger = logging.getLogger(__name__)

# Create blueprint for Plaid connect functions
bp = func.Blueprint()


@bp.route(route="plaid/link-token", methods=["POST", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
@rate_limit(limit=5, window_seconds=60)  # 5 link tokens per minute
async def create_link_token(req: func.HttpRequest) -> func.HttpResponse:
    """
    Create a Plaid Link token for the frontend

    Expected request body:
    {
        "user_id": "string",
        "user_email": "string"
    }
    """
    headers = get_cors_headers()

    # Handle preflight
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    logger.info("Creating Plaid link token")

    try:
        # Parse request body
        req_body = req.get_json()
        user_id = req_body.get("user_id")
        user_email = req_body.get("user_email")

        # Validate user_id
        is_valid, error_msg = validate_user_id(user_id)
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

        # Validate email format
        is_valid, error_msg = validate_email(user_email)
        if not is_valid:
            return func.HttpResponse(
                json.dumps({"error": error_msg}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Create Plaid client and generate link token
        plaid_client = PlaidClient()
        result = plaid_client.create_link_token(user_id, user_email)

        logger.info(f"Link token created successfully for user {user_id}")

        return func.HttpResponse(
            json.dumps(result),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        logger.error(f"Error creating link token: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to create link token. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )


@bp.route(route="plaid/exchange-token", methods=["POST", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
@rate_limit(limit=10, window_seconds=60)  # 10 token exchanges per minute
async def exchange_public_token(req: func.HttpRequest) -> func.HttpResponse:
    """
    Exchange Plaid public token for access token and save accounts to database

    Expected request body:
    {
        "public_token": "string",
        "user_id": "string",
        "user_email": "string",
        "user_name": "string" (optional),
        "family_member_id": int (optional)
    }
    """
    headers = get_cors_headers()

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    logger.info("Exchanging Plaid public token")

    try:
        req_body = req.get_json()
        public_token = req_body.get("public_token")
        user_id = req_body.get("user_id")
        user_email = req_body.get("user_email")
        user_name = req_body.get("user_name", "")
        family_member_id = req_body.get("family_member_id")

        # Validate public_token
        is_valid, error_msg = validate_plaid_token(public_token, "public_token")
        if not is_valid:
            return func.HttpResponse(
                json.dumps({"error": error_msg}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate user_id
        is_valid, error_msg = validate_user_id(user_id)
        if not is_valid:
            return func.HttpResponse(
                json.dumps({"error": error_msg}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate user_name if provided
        if user_name:
            is_valid, error_msg = validate_string(user_name, "user_name", required=False, max_length=200)
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

        # Exchange token with Plaid
        plaid_client = PlaidClient()
        token_result = plaid_client.exchange_public_token(public_token)
        access_token = token_result["access_token"]
        item_id = token_result["item_id"]

        # Get accounts info from Plaid
        accounts = plaid_client.get_accounts(access_token)

        # Initialize database manager
        db = get_db_manager()

        # Parse user name
        first_name = ""
        last_name = ""
        if user_name:
            name_parts = user_name.split(" ", 1)
            first_name = name_parts[0] if len(name_parts) > 0 else ""
            last_name = name_parts[1] if len(name_parts) > 1 else ""

        # Create or update user in database
        db.create_or_update_user(
            user_id=user_id,
            email=user_email or f"{user_id}@example.com",
            first_name=first_name,
            last_name=last_name
        )
        logger.info(f"User saved/updated: {user_email}")

        # Save each account to database
        saved_accounts = []
        for account in accounts:
            saved_account = db.create_account(
                user_id=user_id,
                plaid_account_id=account["account_id"],
                plaid_access_token=access_token,
                account_type=account["type"],
                account_name=account["name"],
                mask=account.get("mask"),
                currency=account["balances"].get("currency", "USD"),
                family_member_id=family_member_id
            )

            # Save current balance
            db.save_balance(
                account_id=saved_account["account_id"],
                current_balance=account["balances"].get("current", 0),
                available_balance=account["balances"].get("available"),
                currency=account["balances"].get("currency", "USD")
            )

            # Add to response (without sensitive data)
            saved_accounts.append({
                "account_id": saved_account["account_id"],
                "plaid_account_id": account["account_id"],
                "name": account["name"],
                "type": account["type"],
                "subtype": account.get("subtype", ""),
                "mask": account.get("mask"),
                "balances": account["balances"]
            })

        logger.info(f"Saved {len(saved_accounts)} accounts to database for user {user_id}")

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "item_id": item_id,
                "accounts_saved": len(saved_accounts),
                "accounts": saved_accounts
            }),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        logger.error(f"Error exchanging token: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to connect account. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )


@bp.route(route="accounts", methods=["GET", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
@rate_limit(limit=60, window_seconds=60)  # 60 requests per minute
async def get_accounts(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get all saved accounts for a user

    Query parameters:
    - user_id: The user's ID (required)
    - family_member_id: Filter by family member (optional)
    """
    headers = get_cors_headers()

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    logger.info("Getting saved accounts")

    try:
        user_id = req.params.get("user_id")
        family_member_id = req.params.get("family_member_id")

        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id query parameter is required"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate user has access to this user_id
        is_valid, error_response = validate_user_access(req, user_id)
        if not is_valid:
            return error_response

        # Convert family_member_id to int if provided
        family_member_id_int = int(family_member_id) if family_member_id else None

        # Get accounts from database
        db = get_db_manager()
        accounts = db.get_accounts_by_user(user_id, family_member_id=family_member_id_int)

        # Get latest balances for all accounts
        account_balances = db.get_latest_balances_for_accounts([acc["account_id"] for acc in accounts])

        # Format accounts for response
        formatted_accounts = []
        for account in accounts:
            account_id = account["account_id"]
            balance_data = account_balances.get(account_id, {})

            formatted_accounts.append({
                "account_id": account_id,
                "name": account["account_name"],
                "type": account["account_type"],
                "mask": account.get("mask"),
                "currency": account.get("currency", "USD"),
                "institution_name": account.get("institution_name"),
                "family_member_id": account.get("family_member_id"),
                "family_member_name": f"{account.get('family_member_first_name', '')} {account.get('family_member_last_name', '')}".strip() if account.get("family_member_first_name") else None,
                "last_synced_at": str(account.get("last_synced_at", "")) if account.get("last_synced_at") else None,
                "created_at": str(account.get("created_at", "")) if account.get("created_at") else None,
                "balances": {
                    "current": balance_data.get("current_balance", 0),
                    "available": balance_data.get("available_balance"),
                    "currency": balance_data.get("currency", account.get("currency", "USD"))
                }
            })

        logger.info(f"Found {len(formatted_accounts)} accounts for user {user_id}")

        # Audit log the data access
        audit_access(user_id, "accounts", request=req, count=len(formatted_accounts))

        return func.HttpResponse(
            json.dumps({"accounts": formatted_accounts}),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        logger.error(f"Error getting accounts: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to retrieve accounts. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )


@bp.route(route="accounts/{account_id}/family-member", methods=["PUT", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
@rate_limit(limit=30, window_seconds=60)  # 30 updates per minute
async def update_account_family_member(req: func.HttpRequest) -> func.HttpResponse:
    """
    Update the family member for an account

    Path parameters:
    - account_id: The account's ID

    Request body:
    {
        "family_member_id": int or null
    }
    """
    headers = get_cors_headers()

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    try:
        account_id = req.route_params.get("account_id")

        if not account_id:
            return func.HttpResponse(
                json.dumps({"error": "account_id is required"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        req_body = req.get_json()
        family_member_id = req_body.get("family_member_id")

        db = get_db_manager()

        # Get the account to verify it exists and belongs to the user
        account = db.get_account(account_id)
        if not account:
            return func.HttpResponse(
                json.dumps({"error": "Account not found"}),
                status_code=404,
                mimetype="application/json",
                headers=headers
            )

        # Verify account belongs to authenticated user
        is_valid, error_response = validate_user_access(req, account["user_id"])
        if not is_valid:
            return error_response

        # If family_member_id is provided, verify it belongs to the same user
        if family_member_id is not None:
            family_member = db.get_family_member(family_member_id)
            if not family_member:
                return func.HttpResponse(
                    json.dumps({"error": "Family member not found"}),
                    status_code=404,
                    mimetype="application/json",
                    headers=headers
                )
            if family_member["user_id"] != account["user_id"]:
                return func.HttpResponse(
                    json.dumps({"error": "Family member does not belong to this user"}),
                    status_code=403,
                    mimetype="application/json",
                    headers=headers
                )

        # Update the family member for the account
        success = db.update_account_family_member(account_id, family_member_id)
        if not success:
            return func.HttpResponse(
                json.dumps({"error": "Failed to update account"}),
                status_code=500,
                mimetype="application/json",
                headers=headers
            )

        logger.info(f"Updated family member for account {account_id} to {family_member_id}")

        return func.HttpResponse(
            json.dumps({"success": True, "message": "Account family member updated"}),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        logger.error(f"Error updating account family member: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to update account. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )


@bp.route(route="accounts/{account_id}", methods=["DELETE", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
@rate_limit(limit=10, window_seconds=60)  # 10 deletes per minute
async def delete_account(req: func.HttpRequest) -> func.HttpResponse:
    """
    Permanently delete an account and all associated transactions.

    Path parameters:
    - account_id: The account's ID

    Note: This performs a hard delete. Transactions are automatically deleted
    via ON DELETE CASCADE foreign key constraint.
    """
    headers = get_cors_headers()

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    try:
        account_id = req.route_params.get("account_id")

        if not account_id:
            return func.HttpResponse(
                json.dumps({"error": "account_id is required"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        db = get_db_manager()

        # Get account info before deletion for logging and verification
        account_info = db.get_account(account_id)

        if not account_info:
            return func.HttpResponse(
                json.dumps({"error": "Account not found"}),
                status_code=404,
                mimetype="application/json",
                headers=headers
            )

        # Verify account belongs to authenticated user
        user_info = get_user_from_request(req)
        if user_info and account_info.get("user_id") != user_info.get("user_id"):
            return func.HttpResponse(
                json.dumps({"error": "Access denied"}),
                status_code=403,
                mimetype="application/json",
                headers=headers
            )

        account_name = account_info.get("account_name", "Unknown")

        # Hard delete - explicitly delete all related records
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # Delete related records first
            cursor.execute(
                "DELETE FROM plaid_sync_cursors WHERE account_id = %s",
                (account_id,)
            )
            cursor.execute(
                "DELETE FROM data_imports WHERE account_id = %s",
                (account_id,)
            )
            cursor.execute(
                "DELETE FROM transactions WHERE account_id = %s",
                (account_id,)
            )
            cursor.execute(
                "DELETE FROM balances WHERE account_id = %s",
                (account_id,)
            )
            # Finally delete the account
            cursor.execute(
                "DELETE FROM accounts WHERE account_id = %s",
                (account_id,)
            )
            conn.commit()

        logger.info(f"Permanently deleted account: {account_id} ({account_name})")

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "message": f"Account '{account_name}' and all associated transactions have been permanently deleted"
            }),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        logger.error(f"Error deleting account: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to delete account. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )
