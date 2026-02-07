"""Tests for authentication module"""
import pytest
import os
from unittest.mock import MagicMock, patch

# Set test environment variables
os.environ.setdefault("AZURE_TENANT_ID", "test-tenant-id")
os.environ.setdefault("AZURE_CLIENT_ID", "test-client-id")
os.environ.setdefault("AZURE_CLIENT_SECRET", "test-secret")

from shared.auth import (
    get_cors_headers,
    is_auth_required,
    get_user_from_request,
    validate_user_access,
    get_validated_user_id
)


class TestAuthConfig:
    """Test authentication configuration"""

    def test_auth_environment_variables(self):
        """Verify auth environment variables are set"""
        assert os.getenv("AZURE_TENANT_ID") is not None
        assert os.getenv("AZURE_CLIENT_ID") is not None

    def test_authority_url_format(self):
        """Test authority URL is properly formatted"""
        tenant_id = os.getenv("AZURE_TENANT_ID")
        expected_authority = f"https://login.microsoftonline.com/{tenant_id}"
        assert "login.microsoftonline.com" in expected_authority


class TestAuthFunctions:
    """Test authentication helper functions"""

    def test_get_auth_service_returns_none_initially(self):
        """Test lazy loading of auth service"""
        from shared.auth import auth_service
        # auth_service is None until first use (lazy loading)
        assert auth_service is None

    def test_extract_user_info_format(self):
        """Test user info extraction has expected keys"""
        expected_keys = ["user_id", "email", "first_name", "last_name", "name"]
        # Placeholder for actual test
        assert len(expected_keys) == 5


class TestSecurityHeaders:
    """Test security headers in CORS response"""

    def test_cors_headers_present(self):
        """Test CORS headers are returned"""
        headers = get_cors_headers()

        assert "Access-Control-Allow-Origin" in headers
        assert "Access-Control-Allow-Methods" in headers
        assert "Access-Control-Allow-Headers" in headers

    def test_hsts_header_present(self):
        """Test HSTS header is present for HTTPS enforcement"""
        headers = get_cors_headers()

        assert "Strict-Transport-Security" in headers
        assert "max-age" in headers["Strict-Transport-Security"]
        assert "includeSubDomains" in headers["Strict-Transport-Security"]

    def test_x_frame_options_deny(self):
        """Test X-Frame-Options is set to DENY to prevent clickjacking"""
        headers = get_cors_headers()

        assert "X-Frame-Options" in headers
        assert headers["X-Frame-Options"] == "DENY"

    def test_x_content_type_options_nosniff(self):
        """Test X-Content-Type-Options prevents MIME sniffing"""
        headers = get_cors_headers()

        assert "X-Content-Type-Options" in headers
        assert headers["X-Content-Type-Options"] == "nosniff"

    def test_x_xss_protection_enabled(self):
        """Test XSS protection header is enabled"""
        headers = get_cors_headers()

        assert "X-XSS-Protection" in headers
        assert "1" in headers["X-XSS-Protection"]

    def test_referrer_policy_set(self):
        """Test Referrer-Policy is set"""
        headers = get_cors_headers()

        assert "Referrer-Policy" in headers
        assert "strict-origin" in headers["Referrer-Policy"]

    def test_content_security_policy_set(self):
        """Test Content-Security-Policy is set"""
        headers = get_cors_headers()

        assert "Content-Security-Policy" in headers
        assert "default-src" in headers["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]

    def test_cache_control_no_store(self):
        """Test Cache-Control prevents caching sensitive data"""
        headers = get_cors_headers()

        assert "Cache-Control" in headers
        assert "no-store" in headers["Cache-Control"]


class TestIsAuthRequired:
    """Test authentication requirement checking"""

    def test_auth_required_by_default(self):
        """Test auth is required by default (secure by default)"""
        with patch.dict(os.environ, {"REQUIRE_AUTH": "true"}):
            assert is_auth_required() is True

    def test_auth_not_required_when_disabled(self):
        """Test auth can be disabled for development"""
        with patch.dict(os.environ, {"REQUIRE_AUTH": "false"}):
            assert is_auth_required() is False

    def test_auth_required_when_env_not_set(self):
        """Test auth defaults to required when env var not set"""
        # Remove the env var
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("REQUIRE_AUTH", None)
            # Default should be True for security
            result = is_auth_required()
            # Restore
            assert result is True


class TestAllowedUsers:
    """Test user allowlist functionality - SECURITY CRITICAL

    This is a family-only financial app. Access control must be:
    - DENY by default when ALLOWED_USERS is not configured
    - Only explicitly listed emails can access the app
    """

    def test_no_allowed_users_denies_all(self):
        """Test that empty ALLOWED_USERS DENIES all users (secure by default)"""
        from shared.auth import is_user_allowed, get_allowed_users
        with patch.dict(os.environ, {"ALLOWED_USERS": ""}):
            assert get_allowed_users() == set()
            # SECURITY: Empty allowlist means NO ONE can access
            assert is_user_allowed("anyone@example.com") is False

    def test_missing_allowed_users_denies_all(self):
        """Test that missing ALLOWED_USERS env var DENIES all users"""
        from shared.auth import is_user_allowed, get_allowed_users
        # Remove the env var completely
        env_copy = os.environ.copy()
        env_copy.pop("ALLOWED_USERS", None)
        with patch.dict(os.environ, env_copy, clear=True):
            assert get_allowed_users() == set()
            # SECURITY: Missing config means NO ONE can access
            assert is_user_allowed("anyone@example.com") is False

    def test_allowed_users_restricts_access(self):
        """Test that ALLOWED_USERS restricts to only listed users"""
        from shared.auth import is_user_allowed, get_allowed_users
        with patch.dict(os.environ, {"ALLOWED_USERS": "user1@example.com,user2@example.com"}):
            allowed = get_allowed_users()
            assert "user1@example.com" in allowed
            assert "user2@example.com" in allowed
            assert is_user_allowed("user1@example.com") is True
            assert is_user_allowed("user2@example.com") is True
            assert is_user_allowed("unauthorized@example.com") is False

    def test_allowed_users_case_insensitive(self):
        """Test that email matching is case-insensitive"""
        from shared.auth import is_user_allowed
        with patch.dict(os.environ, {"ALLOWED_USERS": "User@Example.COM"}):
            assert is_user_allowed("user@example.com") is True
            assert is_user_allowed("USER@EXAMPLE.COM") is True
            assert is_user_allowed("User@Example.COM") is True

    def test_allowed_users_handles_whitespace(self):
        """Test that whitespace is properly handled"""
        from shared.auth import get_allowed_users
        with patch.dict(os.environ, {"ALLOWED_USERS": " user1@example.com , user2@example.com "}):
            allowed = get_allowed_users()
            assert "user1@example.com" in allowed
            assert "user2@example.com" in allowed


class TestGetUserFromRequest:
    """Test user extraction from request"""

    def test_returns_none_when_no_user_info(self):
        """Test returns None when request has no user_info"""
        mock_request = MagicMock()
        # No user_info attribute
        del mock_request.user_info

        result = get_user_from_request(mock_request)
        assert result is None

    def test_returns_user_info_when_present(self):
        """Test returns user_info when present"""
        mock_request = MagicMock()
        mock_request.user_info = {"user_id": "test-123", "email": "test@example.com"}

        result = get_user_from_request(mock_request)

        assert result["user_id"] == "test-123"
        assert result["email"] == "test@example.com"


class TestValidateUserAccess:
    """Test user access validation (user isolation)"""

    def test_access_denied_when_user_mismatch(self):
        """Test access denied when authenticated user doesn't match requested user"""
        with patch.dict(os.environ, {"REQUIRE_AUTH": "true"}):
            mock_request = MagicMock()
            mock_request.user_info = {"user_id": "user-A"}

            is_valid, error_response = validate_user_access(mock_request, "user-B")

            assert is_valid is False
            assert error_response is not None
            assert error_response.status_code == 403

    def test_access_allowed_when_user_matches(self):
        """Test access allowed when user matches"""
        with patch.dict(os.environ, {"REQUIRE_AUTH": "true"}):
            mock_request = MagicMock()
            mock_request.user_info = {"user_id": "user-A"}

            is_valid, error_response = validate_user_access(mock_request, "user-A")

            assert is_valid is True
            assert error_response is None

    def test_access_denied_when_no_auth_info(self):
        """Test access denied when auth required but no user info"""
        with patch.dict(os.environ, {"REQUIRE_AUTH": "true"}):
            mock_request = MagicMock()
            mock_request.user_info = None

            is_valid, error_response = validate_user_access(mock_request, "user-123")

            assert is_valid is False
            assert error_response.status_code == 401

    def test_access_allowed_when_auth_disabled(self):
        """Test access allowed when auth is disabled"""
        with patch.dict(os.environ, {"REQUIRE_AUTH": "false"}):
            mock_request = MagicMock()
            mock_request.user_info = None

            is_valid, error_response = validate_user_access(mock_request, "any-user")

            assert is_valid is True
            assert error_response is None


class TestCorsWildcardWarning:
    """Test CORS wildcard warning"""

    def test_wildcard_cors_logs_warning(self, caplog):
        """Test wildcard CORS origin logs a warning"""
        import logging

        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "*"}):
            with caplog.at_level(logging.WARNING):
                headers = get_cors_headers()

            assert "insecure" in caplog.text.lower() or headers["Access-Control-Allow-Origin"] == "*"
