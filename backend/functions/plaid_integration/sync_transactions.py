"""
Plaid Sync Transactions Functions
Handles fetching and syncing transactions from Plaid
"""

import azure.functions as func
import logging
import json
import os
from datetime import datetime, timedelta
from shared.plaid_client import PlaidClient
from shared.database import get_db_manager
from shared.auth import require_auth, get_cors_headers, validate_user_access
from shared.rate_limiter import rate_limit

logger = logging.getLogger(__name__)

bp = func.Blueprint()


@bp.route(route="transactions/sync", methods=["POST", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
@rate_limit(limit=2, window_seconds=60)  # 2 syncs per minute (heavy operation)
async def sync_transactions(req: func.HttpRequest) -> func.HttpResponse:
    """
    Sync transactions for a user's accounts from Plaid

    Expected request body:
    {
        "user_id": "string",
        "account_id": "string" (optional - if not provided, syncs all accounts)
    }
    """
    headers = get_cors_headers()

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    logger.info("Starting transaction sync")

    try:
        req_body = req.get_json()
        user_id = req_body.get("user_id")
        specific_account_id = req_body.get("account_id")

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
        plaid_client = PlaidClient()

        # Get accounts to sync
        if specific_account_id:
            account = db.get_account(specific_account_id)
            accounts = [account] if account else []
        else:
            accounts = db.get_accounts_by_user(user_id)

        if not accounts:
            return func.HttpResponse(
                json.dumps({"error": "No accounts found to sync"}),
                status_code=404,
                mimetype="application/json",
                headers=headers
            )

        total_added = 0
        total_modified = 0
        total_removed = 0
        synced_accounts = []

        for account in accounts:
            account_id = account["account_id"]
            access_token = account.get("plaid_access_token")
            plaid_account_id = account.get("plaid_account_id")

            if not access_token:
                logger.warning(f"No access token for account {account_id}")
                continue

            logger.info(f"Syncing account {account_id}, plaid_account_id={plaid_account_id}")

            try:
                # Get current sync cursor (if any)
                cursor = db.get_sync_cursor(account_id)
                account_added = 0
                account_modified = 0
                account_removed = 0

                # Use Plaid's incremental sync - loop until has_more is False
                has_more = True
                while has_more:
                    sync_result = plaid_client.sync_transactions(access_token, cursor)

                    logger.info(f"Sync result for {account_id}: added={len(sync_result['added'])}, modified={len(sync_result['modified'])}, removed={len(sync_result['removed'])}, has_more={sync_result['has_more']}")

                    # Process added transactions
                    for txn in sync_result["added"]:
                        # Only save if this transaction belongs to our account
                        if txn["account_id"] == plaid_account_id:
                            category = ",".join(txn.get("category", [])) if txn.get("category") else None
                            saved_txn = db.save_transaction(
                                account_id=account_id,
                                plaid_transaction_id=txn["transaction_id"],
                                date=str(txn["date"]),
                                amount=txn["amount"],
                                description=txn["name"],
                                category=category,
                                pending=txn.get("pending", False),
                                currency=txn.get("iso_currency_code", "USD"),
                                merchant_name=txn.get("merchant_name"),
                                data_source="plaid"
                            )
                            # Apply category rules if no manual override exists
                            if saved_txn and not saved_txn.get("user_category_id"):
                                merchant = txn.get("merchant_name") or txn.get("name")
                                description = txn.get("name")
                                matched_category = db.apply_category_rules(user_id, merchant, description)
                                if matched_category:
                                    db.update_transaction_category(saved_txn["transaction_id"], matched_category, 'rule')
                            account_added += 1
                            total_added += 1

                    # Process modified transactions
                    for txn in sync_result["modified"]:
                        if txn["account_id"] == plaid_account_id:
                            category = ",".join(txn.get("category", [])) if txn.get("category") else None
                            saved_txn = db.save_transaction(
                                account_id=account_id,
                                plaid_transaction_id=txn["transaction_id"],
                                date=str(txn["date"]),
                                amount=txn["amount"],
                                description=txn["name"],
                                category=category,
                                pending=txn.get("pending", False),
                                currency=txn.get("iso_currency_code", "USD"),
                                merchant_name=txn.get("merchant_name"),
                                data_source="plaid"
                            )
                            # Apply category rules if no manual override exists
                            if saved_txn and saved_txn.get("category_source") != 'manual':
                                merchant = txn.get("merchant_name") or txn.get("name")
                                description = txn.get("name")
                                matched_category = db.apply_category_rules(user_id, merchant, description)
                                if matched_category:
                                    db.update_transaction_category(saved_txn["transaction_id"], matched_category, 'rule')
                            account_modified += 1
                            total_modified += 1

                    # Process removed transactions
                    for txn_id in sync_result["removed"]:
                        db.delete_transaction(txn_id)
                        account_removed += 1
                        total_removed += 1

                    # Update cursor for next iteration
                    cursor = sync_result["next_cursor"]
                    has_more = sync_result["has_more"]

                # Save the final cursor for next sync
                if cursor:
                    db.save_sync_cursor(account_id, cursor)

                # If no transactions found via sync, try historical pull (better for sandbox)
                if account_added == 0 and account_modified == 0:
                    logger.info(f"No transactions from sync, trying historical pull for {account_id}")
                    try:
                        transactions = plaid_client.get_historical_transactions(access_token, years=2)
                        logger.info(f"Historical pull returned {len(transactions)} transactions")

                        # Log unique account IDs from transactions for debugging
                        txn_account_ids = set(t["account_id"] for t in transactions)
                        logger.info(f"Transaction account IDs from Plaid: {txn_account_ids}")
                        logger.info(f"Looking for plaid_account_id: {plaid_account_id}")

                        for txn in transactions:
                            if txn["account_id"] == plaid_account_id:
                                category = ",".join(txn.get("category", [])) if txn.get("category") else None
                                saved_txn = db.save_transaction(
                                    account_id=account_id,
                                    plaid_transaction_id=txn["transaction_id"],
                                    date=str(txn["date"]),
                                    amount=txn["amount"],
                                    description=txn["name"],
                                    category=category,
                                    pending=txn.get("pending", False),
                                    currency=txn.get("iso_currency_code", "USD"),
                                    merchant_name=txn.get("merchant_name"),
                                    data_source="plaid"
                                )
                                # Apply category rules if no manual override exists
                                if saved_txn and not saved_txn.get("user_category_id"):
                                    merchant = txn.get("merchant_name") or txn.get("name")
                                    description = txn.get("name")
                                    matched_category = db.apply_category_rules(user_id, merchant, description)
                                    if matched_category:
                                        db.update_transaction_category(saved_txn["transaction_id"], matched_category, 'rule')
                                account_added += 1
                                total_added += 1
                    except Exception as hist_err:
                        logger.warning(f"Historical pull also failed: {str(hist_err)}")

                synced_accounts.append({
                    "account_id": account_id,
                    "account_name": account.get("account_name"),
                    "plaid_account_id": plaid_account_id,
                    "added": account_added,
                    "modified": account_modified,
                    "removed": account_removed
                })

                logger.info(f"Synced account {account_id}: +{account_added}, ~{account_modified}, -{account_removed}")

            except Exception as e:
                logger.error(f"Error syncing account {account_id}: {str(e)}")
                synced_accounts.append({
                    "account_id": account_id,
                    "account_name": account.get("account_name"),
                    "error": str(e)
                })

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "total_added": total_added,
                "total_modified": total_modified,
                "total_removed": total_removed,
                "accounts": synced_accounts
            }),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        logger.error(f"Error syncing transactions: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "An error occurred. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )


@bp.route(route="transactions/sync-historical", methods=["POST", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
@rate_limit(limit=10, window_seconds=60)  # 10 historical syncs per minute (one per account)
async def sync_historical_transactions(req: func.HttpRequest) -> func.HttpResponse:
    """
    Sync historical transactions (up to 2 years) for initial account setup

    Expected request body:
    {
        "user_id": "string",
        "account_id": "string",
        "years": 2 (optional, default 2)
    }
    """
    headers = get_cors_headers()

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    logger.info("Starting historical transaction sync")

    try:
        req_body = req.get_json()
        user_id = req_body.get("user_id")
        account_id = req_body.get("account_id")
        years = req_body.get("years", 2)

        if not user_id or not account_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id and account_id are required"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate user has access to this user_id
        is_valid, error_response = validate_user_access(req, user_id)
        if not is_valid:
            return error_response

        db = get_db_manager()
        plaid_client = PlaidClient()

        # Get the account
        account = db.get_account(account_id)
        if not account:
            return func.HttpResponse(
                json.dumps({"error": "Account not found"}),
                status_code=404,
                mimetype="application/json",
                headers=headers
            )

        access_token = account.get("plaid_access_token")
        plaid_account_id = account.get("plaid_account_id")

        if not access_token:
            return func.HttpResponse(
                json.dumps({"error": "No access token for this account"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Fetch historical transactions
        transactions = plaid_client.get_historical_transactions(access_token, years)

        # Filter to only this account and save
        saved_count = 0
        for txn in transactions:
            if txn["account_id"] == plaid_account_id:
                category = ",".join(txn.get("category", [])) if txn.get("category") else None
                saved_txn = db.save_transaction(
                    account_id=account_id,
                    plaid_transaction_id=txn["transaction_id"],
                    date=str(txn["date"]),
                    amount=txn["amount"],
                    description=txn["name"],
                    category=category,
                    pending=txn.get("pending", False),
                    currency=txn.get("iso_currency_code", "USD"),
                    merchant_name=txn.get("merchant_name"),
                    data_source="plaid"
                )
                # Apply category rules if no manual override exists
                if saved_txn and not saved_txn.get("user_category_id"):
                    merchant = txn.get("merchant_name") or txn.get("name")
                    description = txn.get("name")
                    matched_category = db.apply_category_rules(user_id, merchant, description)
                    if matched_category:
                        db.update_transaction_category(saved_txn["transaction_id"], matched_category, 'rule')
                saved_count += 1

        logger.info(f"Saved {saved_count} historical transactions for account {account_id}")

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "transactions_saved": saved_count,
                "account_id": account_id
            }),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        logger.error(f"Error syncing historical transactions: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "An error occurred. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )


@bp.route(route="transactions", methods=["GET", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
@rate_limit(limit=60, window_seconds=60)  # 60 requests per minute
async def get_transactions(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get transactions for a user

    Query parameters:
    - user_id: The user's ID (required)
    - account_id: Filter by specific account (optional)
    - family_member_id: Filter by family member (optional)
    - limit: Number of transactions to return (default 100)
    - offset: Pagination offset (default 0)
    """
    headers = get_cors_headers()

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    logger.info("Getting transactions")

    try:
        user_id = req.params.get("user_id")
        account_id = req.params.get("account_id")
        family_member_id = req.params.get("family_member_id")
        limit = int(req.params.get("limit", 100))
        offset = int(req.params.get("offset", 0))

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

        db = get_db_manager()

        if account_id:
            transactions = db.get_transactions_by_account(account_id, limit, offset)
            total_count = db.get_transaction_count_by_user(user_id)
            totals = db.get_transaction_totals_by_user(user_id)
        else:
            transactions = db.get_transactions_by_user(user_id, limit, offset, family_member_id=family_member_id_int)
            total_count = db.get_transaction_count_by_user(user_id, family_member_id=family_member_id_int)
            totals = db.get_transaction_totals_by_user(user_id, family_member_id=family_member_id_int)

        # Format transactions for response
        formatted_transactions = []
        for txn in transactions:
            formatted_transactions.append({
                "transaction_id": txn["transaction_id"],
                "account_id": txn["account_id"],
                "account_name": txn.get("account_name"),
                "account_type": txn.get("account_type"),
                "family_member_name": f"{txn.get('family_member_first_name', '')} {txn.get('family_member_last_name', '')}".strip() if txn.get("family_member_first_name") else None,
                "date": str(txn["date"]) if txn.get("date") else None,
                "amount": float(txn["amount"]) if txn.get("amount") else 0,
                "description": txn.get("description"),
                "merchant_name": txn.get("merchant_name"),
                "category": txn.get("category"),
                "user_category_id": txn.get("user_category_id"),
                "user_category_name": txn.get("user_category_name"),
                "user_category_icon": txn.get("user_category_icon"),
                "user_category_color": txn.get("user_category_color"),
                "category_source": txn.get("category_source", "plaid"),
                "pending": bool(txn.get("pending")),
                "currency": txn.get("currency", "USD"),
                "data_source": txn.get("data_source", "plaid")
            })

        logger.info(f"Found {len(formatted_transactions)} transactions for user {user_id}")

        return func.HttpResponse(
            json.dumps({
                "transactions": formatted_transactions,
                "total_count": total_count,
                "totals": totals,
                "limit": limit,
                "offset": offset
            }),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        logger.error(f"Error getting transactions: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "An error occurred. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )
