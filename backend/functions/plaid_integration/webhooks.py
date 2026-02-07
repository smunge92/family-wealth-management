"""
Plaid Webhooks - Handle incoming webhook events from Plaid
Implements signature verification and event processing
"""
import azure.functions as func
import json
import logging
import hashlib
import hmac
import time
import os
import jwt
import requests
from typing import Dict, Optional
from shared.database import DatabaseManager
from shared.auth import get_cors_headers

logger = logging.getLogger(__name__)
bp = func.Blueprint()

# In-memory idempotency cache (use Redis in production for multi-instance)
_processed_webhooks: Dict[str, float] = {}
IDEMPOTENCY_WINDOW_SECONDS = 3600  # 1 hour

# Cache for Plaid's webhook verification key
_webhook_verification_key_cache: Dict[str, dict] = {}
VERIFICATION_KEY_CACHE_SECONDS = 86400  # 24 hours


def get_plaid_webhook_verification_key(key_id: str) -> Optional[dict]:
    """
    Get the webhook verification key from Plaid's API.

    Args:
        key_id: The key ID from the JWT header

    Returns:
        The JWK (JSON Web Key) for verification, or None if not found
    """
    cache_key = f"{key_id}"
    current_time = time.time()

    # Check cache first
    if cache_key in _webhook_verification_key_cache:
        cached = _webhook_verification_key_cache[cache_key]
        if current_time - cached["cached_at"] < VERIFICATION_KEY_CACHE_SECONDS:
            return cached["key"]

    # Fetch from Plaid
    try:
        plaid_client_id = os.getenv("PLAID_CLIENT_ID")
        plaid_secret = os.getenv("PLAID_SECRET")
        plaid_env = os.getenv("PLAID_ENV")

        # Validate PLAID_ENV is explicitly set - no dangerous defaults
        if not plaid_env:
            logger.error("PLAID_ENV environment variable is not set")
            return None

        if plaid_env not in ["sandbox", "development", "production"]:
            logger.error(f"Invalid PLAID_ENV value: {plaid_env}")
            return None

        if plaid_env == "production":
            base_url = "https://production.plaid.com"
        elif plaid_env == "development":
            base_url = "https://development.plaid.com"
        else:
            base_url = "https://sandbox.plaid.com"

        response = requests.post(
            f"{base_url}/webhook_verification_key/get",
            json={
                "client_id": plaid_client_id,
                "secret": plaid_secret,
                "key_id": key_id
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code != 200:
            logger.error(f"Failed to get webhook verification key: {response.text}")
            return None

        result = response.json()
        key = result.get("key")

        if key:
            _webhook_verification_key_cache[cache_key] = {
                "key": key,
                "cached_at": current_time
            }
            return key

        return None

    except Exception as e:
        logger.error(f"Error fetching webhook verification key: {str(e)}")
        return None


def verify_plaid_webhook_signature(body: bytes, signature: str, webhook_id: str) -> bool:
    """
    Verify Plaid webhook signature using JWT verification.

    Plaid signs webhooks using a JWT in the Plaid-Verification header.
    We verify this JWT using Plaid's webhook verification key.

    Args:
        body: Raw request body bytes
        signature: Plaid-Verification header value (JWT)
        webhook_id: The webhook_id from the payload (not used in JWT verification)

    Returns:
        True if signature is valid
    """
    if not signature:
        logger.warning("No Plaid-Verification signature provided")
        return False

    try:
        # Decode the JWT header without verification to get the key ID
        unverified_header = jwt.get_unverified_header(signature)
        key_id = unverified_header.get("kid")

        if not key_id:
            logger.warning("No key ID in JWT header")
            return False

        # Get the verification key from Plaid
        jwk = get_plaid_webhook_verification_key(key_id)
        if not jwk:
            logger.error(f"Could not get verification key for key_id: {key_id}")
            return False

        # Convert JWK to public key
        # Plaid uses ES256 (ECDSA with P-256 curve)
        public_key = jwt.algorithms.ECAlgorithm.from_jwk(json.dumps(jwk))

        # Verify and decode the JWT
        # The JWT claim contains the request body hash
        decoded = jwt.decode(
            signature,
            public_key,
            algorithms=["ES256"],
            options={"verify_aud": False}  # Plaid doesn't use audience
        )

        # Verify the request body hash matches
        expected_body_hash = decoded.get("request_body_sha256")
        if expected_body_hash:
            actual_body_hash = hashlib.sha256(body).hexdigest()
            if expected_body_hash != actual_body_hash:
                logger.warning("Request body hash mismatch")
                return False

        # Check if the token is expired (JWT library does this, but let's be explicit)
        issued_at = decoded.get("iat", 0)
        if time.time() - issued_at > 300:  # 5 minutes
            logger.warning("Webhook JWT is too old")
            return False

        logger.info("Webhook signature verified successfully")
        return True

    except jwt.ExpiredSignatureError:
        logger.warning("Webhook JWT has expired")
        return False
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid webhook JWT: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Signature verification error: {str(e)}")
        return False


def is_duplicate_webhook(webhook_id: str) -> bool:
    """
    Check if webhook has already been processed (idempotency)

    Args:
        webhook_id: Unique webhook identifier

    Returns:
        True if already processed
    """
    current_time = time.time()

    # Clean up old entries
    expired_keys = [
        k for k, v in _processed_webhooks.items()
        if current_time - v > IDEMPOTENCY_WINDOW_SECONDS
    ]
    for key in expired_keys:
        del _processed_webhooks[key]

    if webhook_id in _processed_webhooks:
        logger.info(f"Duplicate webhook detected: {webhook_id}")
        return True

    _processed_webhooks[webhook_id] = current_time
    return False


def handle_transactions_webhook(webhook_code: str, item_id: str, payload: dict) -> dict:
    """
    Handle TRANSACTIONS webhook events

    Args:
        webhook_code: Specific transaction event type
        item_id: Plaid item ID
        payload: Full webhook payload

    Returns:
        Processing result
    """
    db = DatabaseManager()

    if webhook_code == "SYNC_UPDATES_AVAILABLE":
        # New transactions available - trigger sync
        logger.info(f"Transactions sync available for item: {item_id}")

        # Find accounts linked to this item and mark for sync
        try:
            accounts = db.execute_query(
                "SELECT account_id, user_id FROM plaid_accounts WHERE plaid_item_id = %s AND is_active = 1",
                (item_id,)
            )

            for account in accounts:
                # Mark account as needing sync
                db.execute_query(
                    "UPDATE plaid_accounts SET last_webhook_sync = GETUTCDATE(), needs_sync = 1 WHERE account_id = %s",
                    (account['account_id'],)
                )
                logger.info(f"Marked account {account['account_id']} for sync")

            return {"status": "success", "accounts_marked": len(accounts)}
        except Exception as e:
            logger.error(f"Error processing SYNC_UPDATES_AVAILABLE: {str(e)}")
            return {"status": "error", "message": "Failed to process sync update"}

    elif webhook_code == "TRANSACTIONS_REMOVED":
        # Transactions were removed - need to delete them
        removed_transactions = payload.get("removed_transactions", [])
        logger.info(f"Removing {len(removed_transactions)} transactions for item: {item_id}")

        try:
            for txn_id in removed_transactions:
                db.execute_query(
                    "DELETE FROM transactions WHERE plaid_transaction_id = %s",
                    (txn_id,)
                )
            return {"status": "success", "transactions_removed": len(removed_transactions)}
        except Exception as e:
            logger.error(f"Error removing transactions: {str(e)}")
            return {"status": "error", "message": "Failed to remove transactions"}

    elif webhook_code == "INITIAL_UPDATE":
        logger.info(f"Initial transaction update complete for item: {item_id}")
        return {"status": "success", "message": "Initial update acknowledged"}

    elif webhook_code == "HISTORICAL_UPDATE":
        logger.info(f"Historical transaction update complete for item: {item_id}")
        return {"status": "success", "message": "Historical update acknowledged"}

    else:
        logger.warning(f"Unknown transaction webhook code: {webhook_code}")
        return {"status": "ignored", "message": f"Unknown webhook code: {webhook_code}"}


def handle_item_webhook(webhook_code: str, item_id: str, payload: dict) -> dict:
    """
    Handle ITEM webhook events

    Args:
        webhook_code: Specific item event type
        item_id: Plaid item ID
        payload: Full webhook payload

    Returns:
        Processing result
    """
    db = DatabaseManager()

    if webhook_code == "ERROR":
        error = payload.get("error", {})
        error_code = error.get("error_code", "UNKNOWN")
        error_message = error.get("error_message", "Unknown error")

        logger.error(f"Item error for {item_id}: {error_code} - {error_message}")

        try:
            # Update account status
            db.execute_query(
                """UPDATE plaid_accounts
                   SET is_active = 0,
                       error_code = %s,
                       error_message = %s,
                       updated_at = GETUTCDATE()
                   WHERE plaid_item_id = %s""",
                (error_code, error_message[:500], item_id)
            )
            return {"status": "success", "message": "Item error recorded"}
        except Exception as e:
            logger.error(f"Error updating item status: {str(e)}")
            return {"status": "error", "message": "Failed to update item status"}

    elif webhook_code == "PENDING_EXPIRATION":
        # Item access will expire soon - user needs to re-authenticate
        consent_expiration = payload.get("consent_expiration_time")
        logger.warning(f"Item {item_id} pending expiration at {consent_expiration}")

        try:
            db.execute_query(
                """UPDATE plaid_accounts
                   SET needs_reauth = 1,
                       consent_expiration = %s,
                       updated_at = GETUTCDATE()
                   WHERE plaid_item_id = %s""",
                (consent_expiration, item_id)
            )
            return {"status": "success", "message": "Expiration warning recorded"}
        except Exception as e:
            logger.error(f"Error recording expiration: {str(e)}")
            return {"status": "error", "message": "Failed to record expiration"}

    elif webhook_code == "LOGIN_REQUIRED":
        # User needs to re-authenticate with their bank
        logger.warning(f"Login required for item: {item_id}")

        try:
            db.execute_query(
                """UPDATE plaid_accounts
                   SET needs_reauth = 1,
                       error_code = 'ITEM_LOGIN_REQUIRED',
                       updated_at = GETUTCDATE()
                   WHERE plaid_item_id = %s""",
                (item_id,)
            )
            return {"status": "success", "message": "Re-authentication required"}
        except Exception as e:
            logger.error(f"Error updating reauth status: {str(e)}")
            return {"status": "error", "message": "Failed to update reauth status"}

    elif webhook_code == "WEBHOOK_UPDATE_ACKNOWLEDGED":
        logger.info(f"Webhook URL update acknowledged for item: {item_id}")
        return {"status": "success", "message": "Webhook update acknowledged"}

    else:
        logger.warning(f"Unknown item webhook code: {webhook_code}")
        return {"status": "ignored", "message": f"Unknown webhook code: {webhook_code}"}


@bp.function_name("plaid_webhook")
@bp.route(route="plaid/webhook", methods=["POST"])
def plaid_webhook_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle incoming Plaid webhooks

    Plaid sends webhooks for:
    - TRANSACTIONS: New transactions, removals, sync updates
    - ITEM: Errors, login required, pending expiration
    - HOLDINGS: Investment updates (if using Investments product)
    - LIABILITIES: Liability updates (if using Liabilities product)
    """
    headers = get_cors_headers()

    try:
        # Get signature from header
        signature = req.headers.get("Plaid-Verification")

        # Parse request body
        try:
            body = req.get_body()
            payload = json.loads(body)
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Invalid webhook payload: {str(e)}")
            return func.HttpResponse(
                json.dumps({"error": "Invalid request body"}),
                status_code=400,
                headers=headers,
                mimetype="application/json"
            )

        # Extract webhook metadata
        webhook_type = payload.get("webhook_type")
        webhook_code = payload.get("webhook_code")
        item_id = payload.get("item_id")
        webhook_id = payload.get("webhook_id", f"{webhook_type}_{webhook_code}_{item_id}_{time.time()}")

        logger.info(f"Received webhook: type={webhook_type}, code={webhook_code}, item={item_id}")

        # Verify signature
        if not verify_plaid_webhook_signature(body, signature, webhook_id):
            logger.warning(f"Invalid webhook signature for {webhook_id}")
            return func.HttpResponse(
                json.dumps({"error": "Invalid signature"}),
                status_code=401,
                headers=headers,
                mimetype="application/json"
            )

        # Check for duplicate (idempotency)
        if is_duplicate_webhook(webhook_id):
            return func.HttpResponse(
                json.dumps({"status": "already_processed"}),
                status_code=200,
                headers=headers,
                mimetype="application/json"
            )

        # Process based on webhook type
        result = {"status": "unknown_type"}

        if webhook_type == "TRANSACTIONS":
            result = handle_transactions_webhook(webhook_code, item_id, payload)

        elif webhook_type == "ITEM":
            result = handle_item_webhook(webhook_code, item_id, payload)

        elif webhook_type == "HOLDINGS":
            # Investment holdings updated
            logger.info(f"Holdings webhook received for item: {item_id}")
            result = {"status": "acknowledged", "message": "Holdings webhook received"}

        elif webhook_type == "LIABILITIES":
            # Liabilities updated
            logger.info(f"Liabilities webhook received for item: {item_id}")
            result = {"status": "acknowledged", "message": "Liabilities webhook received"}

        elif webhook_type == "AUTH":
            # Auth data changed
            logger.info(f"Auth webhook received for item: {item_id}")
            result = {"status": "acknowledged", "message": "Auth webhook received"}

        else:
            logger.warning(f"Unknown webhook type: {webhook_type}")
            result = {"status": "ignored", "message": f"Unknown type: {webhook_type}"}

        return func.HttpResponse(
            json.dumps(result),
            status_code=200,
            headers=headers,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        # Return 200 to prevent Plaid from retrying (we've logged the error)
        return func.HttpResponse(
            json.dumps({"status": "error", "message": "Internal processing error"}),
            status_code=200,
            headers=headers,
            mimetype="application/json"
        )
