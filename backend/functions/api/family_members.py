"""
Family Members API Functions
Handles CRUD operations for family members
"""

import azure.functions as func
import logging
import json
import os
from shared.database import get_db_manager
from shared.auth import require_auth, get_cors_headers, validate_user_access, get_user_from_request
from shared.rate_limiter import rate_limit
from shared.validation import validate_user_id, validate_string, validate_email

logger = logging.getLogger(__name__)

# Create blueprint for family members API
bp = func.Blueprint()


@bp.route(route="family-members", methods=["GET", "POST", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
@rate_limit(limit=60, window_seconds=60)  # 60 requests per minute
async def family_members_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle family members operations (GET list, POST create)

    GET: Get all family members for a user
    Query parameters:
    - user_id: The user's ID (required)

    POST: Create a new family member
    Expected request body:
    {
        "user_id": "string",
        "first_name": "string",
        "last_name": "string",
        "email": "string" (optional),
        "is_primary": boolean (optional)
    }
    """
    headers = get_cors_headers()

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    if req.method == "GET":
        return await _get_family_members(req, headers)
    elif req.method == "POST":
        return await _create_family_member(req, headers)
    else:
        return func.HttpResponse(
            json.dumps({"error": "Method not allowed"}),
            status_code=405,
            mimetype="application/json",
            headers=headers
        )


async def _get_family_members(req: func.HttpRequest, headers: dict) -> func.HttpResponse:
    """Get all family members for a user"""
    logger.info("Getting family members")

    try:
        user_id = req.params.get("user_id")

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

        # Get family members from database
        db = get_db_manager()
        family_members = db.get_family_members_by_user(user_id)

        # Format for response
        formatted_members = []
        for member in family_members:
            formatted_members.append({
                "family_member_id": member["family_member_id"],
                "first_name": member["first_name"],
                "last_name": member["last_name"],
                "email": member.get("email"),
                "is_primary": bool(member.get("is_primary", False)),
                "created_at": str(member.get("created_at", "")) if member.get("created_at") else None
            })

        logger.info(f"Found {len(formatted_members)} family members for user {user_id}")

        return func.HttpResponse(
            json.dumps({"family_members": formatted_members}),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        logger.error(f"Error getting family members: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to retrieve family members. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )


async def _create_family_member(req: func.HttpRequest, headers: dict) -> func.HttpResponse:
    """Create a new family member"""
    logger.info("Creating family member")

    try:
        req_body = req.get_json()
        user_id = req_body.get("user_id")
        first_name = req_body.get("first_name")
        last_name = req_body.get("last_name")
        email = req_body.get("email")
        is_primary = req_body.get("is_primary", False)

        # Validate user_id
        is_valid, error_msg = validate_user_id(user_id)
        if not is_valid:
            return func.HttpResponse(
                json.dumps({"error": error_msg}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate first_name
        is_valid, error_msg = validate_string(first_name, "first_name", required=True, max_length=100)
        if not is_valid:
            return func.HttpResponse(
                json.dumps({"error": error_msg}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate last_name
        is_valid, error_msg = validate_string(last_name, "last_name", required=True, max_length=100)
        if not is_valid:
            return func.HttpResponse(
                json.dumps({"error": error_msg}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate email if provided
        if email:
            is_valid, error_msg = validate_email(email)
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

        # Create family member in database
        db = get_db_manager()

        # Ensure user exists in database (required for foreign key constraint)
        # This handles the case where the database was cleaned but the user signs in again
        user_info = get_user_from_request(req)
        if user_info:
            db.create_or_update_user(
                user_id=user_id,
                email=user_info.get("email", ""),
                first_name=user_info.get("first_name"),
                last_name=user_info.get("last_name")
            )
        else:
            # Fallback: Check if user exists in database
            # If not, we can't create the family member due to foreign key constraint
            existing_user = db.get_user(user_id)
            if not existing_user:
                logger.warning(f"User {user_id} not found in database and no user_info available to create")
                return func.HttpResponse(
                    json.dumps({
                        "error": "User session not found. Please sign out and sign back in.",
                        "code": "USER_NOT_FOUND"
                    }),
                    status_code=400,
                    mimetype="application/json",
                    headers=headers
                )

        family_member = db.create_family_member(
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            is_primary=is_primary
        )

        logger.info(f"Created family member: {first_name} {last_name}")

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "family_member": {
                    "family_member_id": family_member["family_member_id"],
                    "first_name": family_member["first_name"],
                    "last_name": family_member["last_name"],
                    "email": family_member.get("email"),
                    "is_primary": bool(family_member.get("is_primary", False)),
                    "created_at": str(family_member.get("created_at", "")) if family_member.get("created_at") else None
                }
            }),
            status_code=201,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        error_str = str(e)
        logger.error(f"Error creating family member: {error_str}")

        # Check for unique constraint violation
        if "UQ_family_member_name" in error_str or "duplicate" in error_str.lower():
            return func.HttpResponse(
                json.dumps({"error": "A family member with this name already exists"}),
                status_code=409,
                mimetype="application/json",
                headers=headers
            )

        # Check for foreign key constraint violation (user doesn't exist)
        if "FK_family_members_user" in error_str or "foreign key constraint" in error_str.lower():
            logger.error("Foreign key constraint violation - user does not exist in database")
            return func.HttpResponse(
                json.dumps({
                    "error": "User session not found. Please sign out and sign back in.",
                    "code": "FK_VIOLATION"
                }),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        return func.HttpResponse(
            json.dumps({"error": "Failed to create family member. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )


@bp.route(route="family-members/{family_member_id}", methods=["DELETE", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
@rate_limit(limit=10, window_seconds=60)  # 10 deletes per minute
async def delete_family_member(req: func.HttpRequest) -> func.HttpResponse:
    """
    Delete a family member and optionally cascade delete all associated data.

    Path parameters:
    - family_member_id: The family member's ID

    Query parameters:
    - cascade: "true" (default) to delete all accounts/transactions, "false" to only unlink accounts
    """
    headers = get_cors_headers()

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    try:
        family_member_id = req.route_params.get("family_member_id")

        if not family_member_id:
            return func.HttpResponse(
                json.dumps({"error": "family_member_id is required"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Check for cascade parameter (default to true for safety - delete all data)
        cascade_param = req.params.get("cascade", "true").lower()
        cascade_delete = cascade_param != "false"

        # Get family member info before deletion for logging
        db = get_db_manager()
        family_member = db.get_family_member(int(family_member_id))

        if not family_member:
            return func.HttpResponse(
                json.dumps({"error": "Family member not found"}),
                status_code=404,
                mimetype="application/json",
                headers=headers
            )

        # Validate user has access to this family member
        family_member_user_id = family_member.get("user_id")
        is_valid, error_response = validate_user_access(req, family_member_user_id)
        if not is_valid:
            return error_response

        member_name = f"{family_member['first_name']} {family_member['last_name']}"

        # Delete family member from database with cascade
        result = db.delete_family_member(int(family_member_id), cascade_delete=cascade_delete)

        if not result["deleted"]:
            return func.HttpResponse(
                json.dumps({"error": "Failed to delete family member"}),
                status_code=500,
                mimetype="application/json",
                headers=headers
            )

        logger.info(f"Deleted family member: {member_name} (ID: {family_member_id})")
        logger.info(f"Cascade delete stats: {result['accounts_deleted']} accounts, "
                   f"{result['transactions_deleted']} transactions, "
                   f"{result['balances_deleted']} balances deleted")

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "message": f"Family member '{member_name}' deleted successfully",
                "deleted_data": {
                    "accounts": result["accounts_deleted"],
                    "transactions": result["transactions_deleted"],
                    "balances": result["balances_deleted"]
                }
            }),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        logger.error(f"Error deleting family member: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to delete family member. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )
