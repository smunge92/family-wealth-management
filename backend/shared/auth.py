"""
Azure Entra ID (Azure AD) authentication middleware for Azure Functions
"""

import os
import logging
import json
import jwt
from typing import Optional, Dict, Callable
from functools import wraps
import asyncio
import azure.functions as func
from msal import ConfidentialClientApplication
import requests

logger = logging.getLogger(__name__)


def get_cors_headers():
    """
    Get security headers for responses.

    CORS is handled at the Azure Functions platform level (Function App > API > CORS),
    NOT in code. Setting CORS_ALLOWED_ORIGINS as an environment variable crashes the
    Azure Functions .NET host. Only security headers are set here.
    """
    return {
        # Security headers
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",  # HSTS - enforce HTTPS
        "X-Frame-Options": "DENY",  # Prevent clickjacking
        "X-Content-Type-Options": "nosniff",  # Prevent MIME type sniffing
        "X-XSS-Protection": "1; mode=block",  # XSS filter
        "Referrer-Policy": "strict-origin-when-cross-origin",  # Control referrer info
        "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'",  # CSP
        "Cache-Control": "no-store, no-cache, must-revalidate",  # Prevent caching sensitive data
        "Pragma": "no-cache",  # HTTP/1.0 cache control
    }


# Check if authentication is required
def is_auth_required():
    """Check if authentication is required based on environment"""
    # Default to TRUE for security - explicitly set REQUIRE_AUTH=false only in local development
    return os.getenv("REQUIRE_AUTH", "true").lower() == "true"


def get_allowed_users() -> set:
    """
    Get the list of allowed user emails from environment variable.

    Set ALLOWED_USERS as a comma-separated list of email addresses:
    ALLOWED_USERS=user1@example.com,user2@example.com,user3@example.com

    SECURITY: If not set or empty, NO users are allowed (secure by default).
    This is a financial app - we default to DENY, not ALLOW.
    """
    allowed_users_str = os.getenv("ALLOWED_USERS", "").strip()
    if not allowed_users_str:
        logger.warning("ALLOWED_USERS environment variable is not set or empty. All access will be denied.")
        return set()  # Empty set means NO ONE is allowed

    # Parse comma-separated list and normalize to lowercase
    return {email.strip().lower() for email in allowed_users_str.split(",") if email.strip()}


def is_user_allowed(email: str) -> bool:
    """
    Check if a user's email is in the allowed list.

    SECURITY: This is a family-only financial app.
    - If ALLOWED_USERS is not configured, ALL users are DENIED (secure by default)
    - Only explicitly listed email addresses can access the app

    Returns True if:
    - User's email is in the ALLOWED_USERS list

    Returns False if:
    - ALLOWED_USERS is not set or empty (secure default - DENY ALL)
    - User's email is not in the allowed list
    """
    allowed_users = get_allowed_users()

    # SECURITY: If no allowed users configured, DENY ALL ACCESS
    # This is a financial app - we default to secure (deny) not open (allow)
    if not allowed_users:
        logger.error(f"Access DENIED for {email}: ALLOWED_USERS not configured. "
                    "Set ALLOWED_USERS environment variable with comma-separated family emails.")
        return False

    # Check if user's email is in the allowed list (case-insensitive)
    is_allowed = email.lower() in allowed_users
    if not is_allowed:
        logger.warning(f"Access DENIED for {email}: Not in ALLOWED_USERS list")

    return is_allowed


class AuthConfig:
    """Authentication configuration"""

    TENANT_ID = os.getenv("AZURE_TENANT_ID")
    CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
    CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
    AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
    SCOPE = [f"api://{CLIENT_ID}/.default"]
    JWKS_URI = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"


class AuthService:
    """Handles authentication with Azure Entra ID"""

    def __init__(self):
        self.config = AuthConfig()
        self.msal_app = ConfidentialClientApplication(
            self.config.CLIENT_ID,
            authority=self.config.AUTHORITY,
            client_credential=self.config.CLIENT_SECRET,
        )
        self._jwks_client = None

    def _get_jwks_client(self):
        """Get JWKS (JSON Web Key Set) for token validation"""
        if not self._jwks_client:
            response = requests.get(self.config.JWKS_URI)
            self._jwks_client = response.json()
        return self._jwks_client

    def validate_token(self, token: str) -> Optional[Dict]:
        """
        Validate JWT token from Azure Entra ID

        Args:
            token: JWT token string

        Returns:
            Decoded token payload if valid, None otherwise
        """
        try:
            # Decode token header to get kid (key ID)
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            # Get signing key from JWKS
            jwks = self._get_jwks_client()
            signing_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break

            if not signing_key:
                logger.error("Signing key not found in JWKS")
                return None

            # Verify and decode token
            # Accept both CLIENT_ID and api://CLIENT_ID as valid audiences
            # (ID tokens use CLIENT_ID, access tokens use api://CLIENT_ID)
            valid_audiences = [
                self.config.CLIENT_ID,
                f"api://{self.config.CLIENT_ID}",
            ]

            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=valid_audiences,
                options={"verify_iss": False},
            )

            # Manually verify issuer (accept both v1 and v2 formats)
            valid_issuers = [
                f"https://login.microsoftonline.com/{self.config.TENANT_ID}/v2.0",
                f"https://sts.windows.net/{self.config.TENANT_ID}/",
            ]
            if payload.get("iss") not in valid_issuers:
                logger.error(f"Invalid issuer: {payload.get('iss')}")
                return None

            # Warn if this is an ID token being used as a bearer token
            # ID tokens have aud == client_id but no 'scp' or 'roles' claim
            # Access tokens have a 'scp' (scope) claim
            if "scp" not in payload and "roles" not in payload:
                logger.warning(
                    "ID token used as bearer token (no 'scp' or 'roles' claim). "
                    "Consider configuring API scopes for proper access tokens."
                )

            return payload

        except jwt.ExpiredSignatureError:
            logger.error("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error validating token: {str(e)}")
            return None

    def extract_user_info(self, token_payload: Dict) -> Dict:
        """
        Extract user information from token payload

        Args:
            token_payload: Decoded JWT payload

        Returns:
            Dictionary with user information
        """
        return {
            "user_id": token_payload.get("oid"),  # Object ID
            "email": token_payload.get("preferred_username") or token_payload.get("upn"),
            "first_name": token_payload.get("given_name"),
            "last_name": token_payload.get("family_name"),
            "name": token_payload.get("name"),
        }


# Lazy-loaded auth service instance
_auth_service = None

def get_auth_service():
    """Get or create the auth service (lazy initialization)"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service

# For backwards compatibility - but prefer using get_auth_service()
auth_service = None  # Will be None until first use


def require_auth(f: Callable) -> Callable:
    """
    Decorator to require authentication for Azure Functions.
    Handles both sync and async functions, and properly includes CORS headers.

    In development mode (REQUIRE_AUTH=false or not set), authentication is optional.
    In production (REQUIRE_AUTH=true), authentication is enforced.

    Usage:
        @bp.route(route="protected", methods=["GET", "OPTIONS"])
        @require_auth
        async def protected_function(req: func.HttpRequest) -> func.HttpResponse:
            user_info = req.user_info  # May be None in dev mode
            return func.HttpResponse(f"Hello {user_info['name'] if user_info else 'Guest'}")
    """

    @wraps(f)
    async def async_wrapper(req: func.HttpRequest, *args, **kwargs) -> func.HttpResponse:
        headers = get_cors_headers()

        # Handle OPTIONS preflight request
        if req.method == "OPTIONS":
            return func.HttpResponse(status_code=204, headers=headers)

        # Check if authentication is required
        auth_required = is_auth_required()

        # Extract token from Authorization header
        auth_header = req.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix

            # Validate token
            try:
                token_payload = get_auth_service().validate_token(token)
                if token_payload:
                    # Extract user info and attach to request
                    user_info = get_auth_service().extract_user_info(token_payload)

                    # Check if user is in the allowed list
                    user_email = user_info.get("email", "")
                    if not is_user_allowed(user_email):
                        logger.warning(f"Access denied for user: {user_email} - not in allowed users list")
                        return func.HttpResponse(
                            json.dumps({"error": "Access denied. You are not authorized to use this application."}),
                            status_code=403,
                            mimetype="application/json",
                            headers=headers
                        )

                    req.user_info = user_info
                elif auth_required:
                    return func.HttpResponse(
                        json.dumps({"error": "Invalid or expired token"}),
                        status_code=401,
                        mimetype="application/json",
                        headers=headers
                    )
                else:
                    req.user_info = None
            except Exception as e:
                logger.error(f"Token validation error: {str(e)}")
                if auth_required:
                    return func.HttpResponse(
                        json.dumps({"error": "Authentication failed"}),
                        status_code=401,
                        mimetype="application/json",
                        headers=headers
                    )
                req.user_info = None
        elif auth_required:
            return func.HttpResponse(
                json.dumps({"error": "Missing or invalid Authorization header"}),
                status_code=401,
                mimetype="application/json",
                headers=headers
            )
        else:
            # No token provided and auth not required - allow request
            req.user_info = None

        # Call the original function (handle both async and sync)
        if asyncio.iscoroutinefunction(f):
            return await f(req, *args, **kwargs)
        else:
            return f(req, *args, **kwargs)

    @wraps(f)
    def sync_wrapper(req: func.HttpRequest, *args, **kwargs) -> func.HttpResponse:
        headers = get_cors_headers()

        # Handle OPTIONS preflight request
        if req.method == "OPTIONS":
            return func.HttpResponse(status_code=204, headers=headers)

        # Check if authentication is required
        auth_required = is_auth_required()

        # Extract token from Authorization header
        auth_header = req.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix

            # Validate token
            try:
                token_payload = get_auth_service().validate_token(token)
                if token_payload:
                    # Extract user info and attach to request
                    user_info = get_auth_service().extract_user_info(token_payload)

                    # Check if user is in the allowed list
                    user_email = user_info.get("email", "")
                    if not is_user_allowed(user_email):
                        logger.warning(f"Access denied for user: {user_email} - not in allowed users list")
                        return func.HttpResponse(
                            json.dumps({"error": "Access denied. You are not authorized to use this application."}),
                            status_code=403,
                            mimetype="application/json",
                            headers=headers
                        )

                    req.user_info = user_info
                elif auth_required:
                    return func.HttpResponse(
                        json.dumps({"error": "Invalid or expired token"}),
                        status_code=401,
                        mimetype="application/json",
                        headers=headers
                    )
                else:
                    req.user_info = None
            except Exception as e:
                logger.error(f"Token validation error: {str(e)}")
                if auth_required:
                    return func.HttpResponse(
                        json.dumps({"error": "Authentication failed"}),
                        status_code=401,
                        mimetype="application/json",
                        headers=headers
                    )
                req.user_info = None
        elif auth_required:
            return func.HttpResponse(
                json.dumps({"error": "Missing or invalid Authorization header"}),
                status_code=401,
                mimetype="application/json",
                headers=headers
            )
        else:
            # No token provided and auth not required - allow request
            req.user_info = None

        # Call the original function
        return f(req, *args, **kwargs)

    # Return appropriate wrapper based on function type
    if asyncio.iscoroutinefunction(f):
        return async_wrapper
    return sync_wrapper


def get_user_from_request(req: func.HttpRequest) -> Optional[Dict]:
    """
    Get authenticated user information from request

    Args:
        req: Azure Functions HttpRequest

    Returns:
        User info dictionary or None if not authenticated
    """
    return getattr(req, "user_info", None)


def validate_user_access(req: func.HttpRequest, requested_user_id: str) -> tuple[bool, Optional[func.HttpResponse]]:
    """
    Validate that the authenticated user has access to the requested resource.

    This is a critical security check to prevent users from accessing
    other users' data.

    Args:
        req: Azure Functions HttpRequest with user_info attached
        requested_user_id: The user_id being requested in the API call

    Returns:
        Tuple of (is_valid, error_response)
        - If valid: (True, None)
        - If invalid: (False, HttpResponse with 403 error)
    """
    headers = get_cors_headers()

    # Get authenticated user from request
    user_info = get_user_from_request(req)

    # If auth is required and no user info, deny access
    if is_auth_required():
        if not user_info:
            return False, func.HttpResponse(
                json.dumps({"error": "Authentication required"}),
                status_code=401,
                mimetype="application/json",
                headers=headers
            )

        # Validate that authenticated user matches requested user
        authenticated_user_id = user_info.get("user_id")
        if authenticated_user_id != requested_user_id:
            logger.warning(
                f"User isolation violation: authenticated user {authenticated_user_id} "
                f"attempted to access data for user {requested_user_id}"
            )
            return False, func.HttpResponse(
                json.dumps({"error": "Access denied"}),
                status_code=403,
                mimetype="application/json",
                headers=headers
            )

    # Access is valid
    return True, None


def get_validated_user_id(req: func.HttpRequest, param_name: str = "user_id") -> tuple[Optional[str], Optional[func.HttpResponse]]:
    """
    Get and validate the user_id from request parameters.

    In authenticated mode, this ensures the user can only access their own data.
    In development mode (auth disabled), allows the provided user_id.

    Args:
        req: Azure Functions HttpRequest
        param_name: Name of the parameter containing user_id (default: "user_id")

    Returns:
        Tuple of (user_id, error_response)
        - If valid: (user_id, None)
        - If invalid: (None, HttpResponse with error)
    """
    headers = get_cors_headers()

    # Get user_id from request params or body
    user_id = req.params.get(param_name)
    if not user_id:
        try:
            body = req.get_json()
            user_id = body.get(param_name)
        except:
            pass

    if not user_id:
        return None, func.HttpResponse(
            json.dumps({"error": f"Missing required parameter: {param_name}"}),
            status_code=400,
            mimetype="application/json",
            headers=headers
        )

    # Validate access
    is_valid, error_response = validate_user_access(req, user_id)
    if not is_valid:
        return None, error_response

    return user_id, None
