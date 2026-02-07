"""
Categories API Functions
Handles CRUD operations for categories and category rules,
and transaction category updates with rule creation.
"""

import azure.functions as func
import logging
import json
import re
from shared.database import get_db_manager
from shared.auth import require_auth, get_cors_headers, validate_user_access
from shared.rate_limiter import rate_limit
from shared.validation import validate_user_id, validate_string

# Hex color pattern: # followed by exactly 6 hex digits
HEX_COLOR_PATTERN = re.compile(r'^#[0-9a-fA-F]{6}$')

logger = logging.getLogger(__name__)

# Create blueprint for categories API
bp = func.Blueprint()


# ==================== CATEGORIES ENDPOINTS ====================

@bp.route(route="categories", methods=["GET", "POST", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
@rate_limit(limit=60, window_seconds=60)
async def categories_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle category operations (GET list, POST create)

    GET: Get all categories for a user (system + custom)
    Query parameters:
    - user_id: The user's ID (required)

    POST: Create a new user category
    Expected request body:
    {
        "user_id": "string",
        "name": "string",
        "icon": "string" (optional, emoji),
        "color": "string" (optional, hex color)
    }
    """
    headers = get_cors_headers()

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    if req.method == "GET":
        return await _get_categories(req, headers)
    elif req.method == "POST":
        return await _create_category(req, headers)
    else:
        return func.HttpResponse(
            json.dumps({"error": "Method not allowed"}),
            status_code=405,
            mimetype="application/json",
            headers=headers
        )


async def _get_categories(req: func.HttpRequest, headers: dict) -> func.HttpResponse:
    """Get all categories for a user (system + custom)"""
    logger.info("Getting categories")

    try:
        user_id = req.params.get("user_id")

        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id query parameter is required"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate user has access
        is_valid, error_response = validate_user_access(req, user_id)
        if not is_valid:
            return error_response

        # Get categories from database
        db = get_db_manager()
        categories = db.get_categories(user_id)

        # Format for response
        formatted_categories = []
        for cat in categories:
            formatted_categories.append({
                "category_id": cat["category_id"],
                "name": cat["name"],
                "icon": cat.get("icon"),
                "color": cat.get("color"),
                "is_system": bool(cat.get("is_system", False)),
                "display_order": cat.get("display_order", 0),
                "created_at": str(cat.get("created_at", "")) if cat.get("created_at") else None
            })

        logger.info(f"Found {len(formatted_categories)} categories for user {user_id}")

        return func.HttpResponse(
            json.dumps({"categories": formatted_categories}),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to retrieve categories. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )


async def _create_category(req: func.HttpRequest, headers: dict) -> func.HttpResponse:
    """Create a new user category"""
    logger.info("Creating category")

    try:
        req_body = req.get_json()
        user_id = req_body.get("user_id")
        name = req_body.get("name")
        icon = req_body.get("icon")
        color = req_body.get("color")

        # Validate user_id
        is_valid, error_msg = validate_user_id(user_id)
        if not is_valid:
            return func.HttpResponse(
                json.dumps({"error": error_msg}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate name
        is_valid, error_msg = validate_string(name, "name", required=True, max_length=100)
        if not is_valid:
            return func.HttpResponse(
                json.dumps({"error": error_msg}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate user has access
        is_valid, error_response = validate_user_access(req, user_id)
        if not is_valid:
            return error_response

        # Validate color format if provided
        if color and not HEX_COLOR_PATTERN.match(color):
            return func.HttpResponse(
                json.dumps({"error": "Color must be a hex color code (e.g., #ff0000)"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Create category in database
        db = get_db_manager()
        category = db.create_category(
            user_id=user_id,
            name=name,
            icon=icon,
            color=color
        )

        logger.info(f"Created category: {name}")

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "category": {
                    "category_id": category["category_id"],
                    "name": category["name"],
                    "icon": category.get("icon"),
                    "color": category.get("color"),
                    "is_system": bool(category.get("is_system", False)),
                    "display_order": category.get("display_order", 0),
                    "created_at": str(category.get("created_at", "")) if category.get("created_at") else None
                }
            }),
            status_code=201,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        error_str = str(e)
        logger.error(f"Error creating category: {error_str}")

        # Check for unique constraint violation
        if "UQ_category_name_user" in error_str or "duplicate" in error_str.lower():
            return func.HttpResponse(
                json.dumps({"error": "A category with this name already exists"}),
                status_code=409,
                mimetype="application/json",
                headers=headers
            )

        return func.HttpResponse(
            json.dumps({"error": "Failed to create category. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )


@bp.route(route="categories/{category_id}", methods=["PUT", "DELETE", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
@rate_limit(limit=30, window_seconds=60)
async def category_detail_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle single category operations (PUT update, DELETE)

    PUT: Update a user category (cannot modify system categories)
    Expected request body:
    {
        "user_id": "string",
        "name": "string" (optional),
        "icon": "string" (optional),
        "color": "string" (optional)
    }

    DELETE: Delete a user category (cannot delete system categories)
    Query parameters:
    - user_id: The user's ID (required)
    """
    headers = get_cors_headers()

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    category_id_str = req.route_params.get("category_id")
    if not category_id_str:
        return func.HttpResponse(
            json.dumps({"error": "category_id is required"}),
            status_code=400,
            mimetype="application/json",
            headers=headers
        )

    try:
        category_id = int(category_id_str)
    except (ValueError, TypeError):
        return func.HttpResponse(
            json.dumps({"error": "category_id must be a valid integer"}),
            status_code=400,
            mimetype="application/json",
            headers=headers
        )

    if req.method == "PUT":
        return await _update_category(req, headers, category_id)
    elif req.method == "DELETE":
        return await _delete_category(req, headers, category_id)
    else:
        return func.HttpResponse(
            json.dumps({"error": "Method not allowed"}),
            status_code=405,
            mimetype="application/json",
            headers=headers
        )


async def _update_category(req: func.HttpRequest, headers: dict, category_id: int) -> func.HttpResponse:
    """Update a user category"""
    logger.info(f"Updating category {category_id}")

    try:
        req_body = req.get_json()
        user_id = req_body.get("user_id")
        name = req_body.get("name")
        icon = req_body.get("icon")
        color = req_body.get("color")

        # Validate user_id
        is_valid, error_msg = validate_user_id(user_id)
        if not is_valid:
            return func.HttpResponse(
                json.dumps({"error": error_msg}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate user has access
        is_valid, error_response = validate_user_access(req, user_id)
        if not is_valid:
            return error_response

        # Validate name if provided
        if name is not None:
            is_valid, error_msg = validate_string(name, "name", required=True, max_length=100)
            if not is_valid:
                return func.HttpResponse(
                    json.dumps({"error": error_msg}),
                    status_code=400,
                    mimetype="application/json",
                    headers=headers
                )

        # Validate color format if provided
        if color and not HEX_COLOR_PATTERN.match(color):
            return func.HttpResponse(
                json.dumps({"error": "Color must be a hex color code (e.g., #ff0000)"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Update category in database
        db = get_db_manager()
        category = db.update_category(
            category_id=category_id,
            user_id=user_id,
            name=name,
            icon=icon,
            color=color
        )

        if not category:
            return func.HttpResponse(
                json.dumps({"error": "Category not found or cannot be modified (system category)"}),
                status_code=404,
                mimetype="application/json",
                headers=headers
            )

        logger.info(f"Updated category {category_id}")

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "category": {
                    "category_id": category["category_id"],
                    "name": category["name"],
                    "icon": category.get("icon"),
                    "color": category.get("color"),
                    "is_system": bool(category.get("is_system", False)),
                    "display_order": category.get("display_order", 0)
                }
            }),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        error_str = str(e)
        logger.error(f"Error updating category: {error_str}")

        if "UQ_category_name_user" in error_str or "duplicate" in error_str.lower():
            return func.HttpResponse(
                json.dumps({"error": "A category with this name already exists"}),
                status_code=409,
                mimetype="application/json",
                headers=headers
            )

        return func.HttpResponse(
            json.dumps({"error": "Failed to update category. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )


async def _delete_category(req: func.HttpRequest, headers: dict, category_id: int) -> func.HttpResponse:
    """Delete a user category"""
    logger.info(f"Deleting category {category_id}")

    try:
        user_id = req.params.get("user_id")

        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id query parameter is required"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate user has access
        is_valid, error_response = validate_user_access(req, user_id)
        if not is_valid:
            return error_response

        # Delete category from database
        db = get_db_manager()
        deleted = db.delete_category(category_id, user_id)

        if not deleted:
            return func.HttpResponse(
                json.dumps({"error": "Category not found or cannot be deleted (system category)"}),
                status_code=404,
                mimetype="application/json",
                headers=headers
            )

        logger.info(f"Deleted category {category_id}")

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "message": "Category deleted successfully"
            }),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        logger.error(f"Error deleting category: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to delete category. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )


# ==================== CATEGORY RULES ENDPOINTS ====================

@bp.route(route="category-rules", methods=["GET", "POST", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
@rate_limit(limit=60, window_seconds=60)
async def category_rules_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle category rules operations (GET list, POST create)

    GET: Get all user's category rules (not system rules)
    Query parameters:
    - user_id: The user's ID (required)

    POST: Create a new category rule and optionally apply to existing transactions
    Expected request body:
    {
        "user_id": "string",
        "category_id": int,
        "match_type": "merchant_contains" | "description_contains",
        "match_value": "string",
        "apply_to_existing": boolean (optional, default true)
    }
    """
    headers = get_cors_headers()

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    if req.method == "GET":
        return await _get_category_rules(req, headers)
    elif req.method == "POST":
        return await _create_category_rule(req, headers)
    else:
        return func.HttpResponse(
            json.dumps({"error": "Method not allowed"}),
            status_code=405,
            mimetype="application/json",
            headers=headers
        )


async def _get_category_rules(req: func.HttpRequest, headers: dict) -> func.HttpResponse:
    """Get all user's category rules"""
    logger.info("Getting category rules")

    try:
        user_id = req.params.get("user_id")

        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id query parameter is required"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate user has access
        is_valid, error_response = validate_user_access(req, user_id)
        if not is_valid:
            return error_response

        # Get user's rules from database (not system rules)
        db = get_db_manager()
        rules = db.get_user_category_rules(user_id)

        # Format for response
        formatted_rules = []
        for rule in rules:
            formatted_rules.append({
                "rule_id": rule["rule_id"],
                "category_id": rule["category_id"],
                "category_name": rule.get("category_name"),
                "category_icon": rule.get("category_icon"),
                "category_color": rule.get("category_color"),
                "match_type": rule["match_type"],
                "match_value": rule["match_value"],
                "priority": rule.get("priority", 50),
                "created_at": str(rule.get("created_at", "")) if rule.get("created_at") else None
            })

        logger.info(f"Found {len(formatted_rules)} rules for user {user_id}")

        return func.HttpResponse(
            json.dumps({"rules": formatted_rules}),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        logger.error(f"Error getting category rules: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to retrieve category rules. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )


async def _create_category_rule(req: func.HttpRequest, headers: dict) -> func.HttpResponse:
    """Create a new category rule"""
    logger.info("Creating category rule")

    try:
        req_body = req.get_json()
        user_id = req_body.get("user_id")
        category_id = req_body.get("category_id")
        match_type = req_body.get("match_type")
        match_value = req_body.get("match_value")
        apply_to_existing = req_body.get("apply_to_existing", True)

        # Validate user_id
        is_valid, error_msg = validate_user_id(user_id)
        if not is_valid:
            return func.HttpResponse(
                json.dumps({"error": error_msg}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate category_id
        if not category_id or not isinstance(category_id, int):
            return func.HttpResponse(
                json.dumps({"error": "category_id is required and must be an integer"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate match_type
        valid_match_types = ["merchant_contains", "description_contains"]
        if match_type not in valid_match_types:
            return func.HttpResponse(
                json.dumps({"error": f"match_type must be one of: {', '.join(valid_match_types)}"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate match_value
        is_valid, error_msg = validate_string(match_value, "match_value", required=True, max_length=200)
        if not is_valid:
            return func.HttpResponse(
                json.dumps({"error": error_msg}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate user has access
        is_valid, error_response = validate_user_access(req, user_id)
        if not is_valid:
            return error_response

        # Create rule in database
        db = get_db_manager()
        rule = db.create_category_rule(
            user_id=user_id,
            category_id=category_id,
            match_type=match_type,
            match_value=match_value
        )

        # Apply to existing transactions if requested
        updated_count = 0
        if apply_to_existing:
            updated_count = db.apply_rule_to_similar_transactions(user_id, rule["rule_id"])

        logger.info(f"Created category rule: {match_type} '{match_value}' -> category {category_id}")
        if updated_count > 0:
            logger.info(f"Applied rule to {updated_count} existing transactions")

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "rule": {
                    "rule_id": rule["rule_id"],
                    "category_id": rule["category_id"],
                    "category_name": rule.get("category_name"),
                    "category_icon": rule.get("category_icon"),
                    "category_color": rule.get("category_color"),
                    "match_type": rule["match_type"],
                    "match_value": rule["match_value"],
                    "priority": rule.get("priority", 50),
                    "created_at": str(rule.get("created_at", "")) if rule.get("created_at") else None
                },
                "transactions_updated": updated_count
            }),
            status_code=201,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        error_str = str(e)
        logger.error(f"Error creating category rule: {error_str}")

        # Check for unique constraint violation
        if "UQ_rule_user_match" in error_str or "duplicate" in error_str.lower():
            return func.HttpResponse(
                json.dumps({"error": "A rule with this match type and value already exists"}),
                status_code=409,
                mimetype="application/json",
                headers=headers
            )

        return func.HttpResponse(
            json.dumps({"error": "Failed to create category rule. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )


@bp.route(route="category-rules/{rule_id}", methods=["DELETE", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
@rate_limit(limit=30, window_seconds=60)
async def delete_category_rule(req: func.HttpRequest) -> func.HttpResponse:
    """
    Delete a user category rule (cannot delete system rules)

    Path parameters:
    - rule_id: The rule's ID

    Query parameters:
    - user_id: The user's ID (required)
    """
    headers = get_cors_headers()

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    try:
        rule_id_str = req.route_params.get("rule_id")
        user_id = req.params.get("user_id")

        if not rule_id_str:
            return func.HttpResponse(
                json.dumps({"error": "rule_id is required"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        try:
            rule_id = int(rule_id_str)
        except (ValueError, TypeError):
            return func.HttpResponse(
                json.dumps({"error": "rule_id must be a valid integer"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id query parameter is required"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate user has access
        is_valid, error_response = validate_user_access(req, user_id)
        if not is_valid:
            return error_response

        # Delete rule from database
        db = get_db_manager()
        deleted = db.delete_category_rule(rule_id, user_id)

        if not deleted:
            return func.HttpResponse(
                json.dumps({"error": "Rule not found or cannot be deleted (system rule)"}),
                status_code=404,
                mimetype="application/json",
                headers=headers
            )

        logger.info(f"Deleted category rule {rule_id}")

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "message": "Rule deleted successfully"
            }),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        logger.error(f"Error deleting category rule: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to delete category rule. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )


# ==================== TRANSACTION CATEGORY ENDPOINT ====================

@bp.route(route="transactions/{transaction_id}/category", methods=["PATCH", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
@rate_limit(limit=120, window_seconds=60)
async def update_transaction_category(req: func.HttpRequest) -> func.HttpResponse:
    """
    Update a transaction's category with optional rule creation.

    Path parameters:
    - transaction_id: The transaction's UUID

    Expected request body:
    {
        "user_id": "string",
        "category_id": int,
        "create_rule": boolean (optional, default false),
        "rule_match_type": "merchant_contains" | "description_contains" (optional)
    }

    Response:
    {
        "success": true,
        "rule_created": boolean,
        "similar_updated": int
    }
    """
    headers = get_cors_headers()

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    try:
        transaction_id = req.route_params.get("transaction_id")
        if not transaction_id:
            return func.HttpResponse(
                json.dumps({"error": "transaction_id is required"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        req_body = req.get_json()
        user_id = req_body.get("user_id")
        category_id = req_body.get("category_id")
        create_rule = req_body.get("create_rule", False)
        rule_match_type = req_body.get("rule_match_type", "merchant_contains")

        # Validate user_id
        is_valid, error_msg = validate_user_id(user_id)
        if not is_valid:
            return func.HttpResponse(
                json.dumps({"error": error_msg}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate category_id
        if category_id is None or not isinstance(category_id, int):
            return func.HttpResponse(
                json.dumps({"error": "category_id is required and must be an integer"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate user has access
        is_valid, error_response = validate_user_access(req, user_id)
        if not is_valid:
            return error_response

        db = get_db_manager()

        # Get the transaction to verify ownership and get merchant info
        transaction = db.get_transaction_by_id(transaction_id)
        if not transaction:
            return func.HttpResponse(
                json.dumps({"error": "Transaction not found"}),
                status_code=404,
                mimetype="application/json",
                headers=headers
            )

        # Verify transaction belongs to user
        if transaction.get("user_id") != user_id:
            return func.HttpResponse(
                json.dumps({"error": "Not authorized to modify this transaction"}),
                status_code=403,
                mimetype="application/json",
                headers=headers
            )

        # Update the transaction category
        updated = db.update_transaction_category(transaction_id, category_id, 'manual')
        if not updated:
            return func.HttpResponse(
                json.dumps({"error": "Failed to update transaction category"}),
                status_code=500,
                mimetype="application/json",
                headers=headers
            )

        rule_created = False
        similar_updated = 0

        # Create rule if requested
        if create_rule:
            # Extract match value from transaction description
            description = transaction.get("description", "")

            if description:
                # For merchant_contains, try to extract a clean merchant name
                # Use the first word or first two words as the match pattern
                match_value = description.strip()

                # Try to create the rule
                try:
                    rule = db.create_category_rule(
                        user_id=user_id,
                        category_id=category_id,
                        match_type=rule_match_type,
                        match_value=match_value
                    )
                    rule_created = True

                    # Apply to similar transactions
                    similar_updated = db.apply_rule_to_similar_transactions(user_id, rule["rule_id"])
                    # Don't count the current transaction
                    if similar_updated > 0:
                        similar_updated -= 1

                    logger.info(f"Created rule for {match_value}, updated {similar_updated} similar transactions")
                except Exception as rule_error:
                    # Rule creation might fail if duplicate - that's okay
                    logger.warning(f"Could not create rule: {str(rule_error)}")

        logger.info(f"Updated transaction {transaction_id} to category {category_id}")

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "rule_created": rule_created,
                "similar_updated": similar_updated
            }),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        logger.error(f"Error updating transaction category: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to update transaction category. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )


@bp.route(route="transactions/similar-count", methods=["GET", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
@rate_limit(limit=60, window_seconds=60)
async def get_similar_transaction_count(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get the count of transactions that would match a rule pattern.
    Used to show "Found X similar transactions" in UI before creating a rule.

    Query parameters:
    - user_id: The user's ID (required)
    - match_type: "merchant_contains" | "description_contains" (required)
    - match_value: The pattern to match (required)
    """
    headers = get_cors_headers()

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    try:
        user_id = req.params.get("user_id")
        match_type = req.params.get("match_type")
        match_value = req.params.get("match_value")

        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id query parameter is required"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        if not match_type or not match_value:
            return func.HttpResponse(
                json.dumps({"error": "match_type and match_value query parameters are required"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # Validate user has access
        is_valid, error_response = validate_user_access(req, user_id)
        if not is_valid:
            return error_response

        db = get_db_manager()
        count = db.count_similar_transactions(user_id, match_type, match_value)

        return func.HttpResponse(
            json.dumps({
                "count": count,
                "match_type": match_type,
                "match_value": match_value
            }),
            status_code=200,
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        logger.error(f"Error getting similar transaction count: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to count similar transactions. Please try again."}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )
