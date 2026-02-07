"""
Tests for audit logging module
"""

import os
import pytest
from unittest.mock import MagicMock, patch
import logging

from shared.audit import (
    AuditAction,
    AuditLogger,
    get_audit_logger,
    audit_log,
    audit_access,
    audit_security_event
)


class TestAuditAction:
    """Test AuditAction enum"""

    def test_data_access_actions_exist(self):
        """Verify data access actions are defined"""
        assert AuditAction.VIEW_ACCOUNTS.value == "view_accounts"
        assert AuditAction.VIEW_TRANSACTIONS.value == "view_transactions"
        assert AuditAction.VIEW_BALANCES.value == "view_balances"

    def test_modification_actions_exist(self):
        """Verify modification actions are defined"""
        assert AuditAction.CREATE_ACCOUNT.value == "create_account"
        assert AuditAction.DELETE_ACCOUNT.value == "delete_account"
        assert AuditAction.DELETE_FAMILY_MEMBER.value == "delete_family_member"

    def test_plaid_actions_exist(self):
        """Verify Plaid-related actions are defined"""
        assert AuditAction.PLAID_LINK_TOKEN.value == "plaid_link_token"
        assert AuditAction.PLAID_TOKEN_EXCHANGE.value == "plaid_token_exchange"
        assert AuditAction.PLAID_SYNC.value == "plaid_sync"

    def test_security_actions_exist(self):
        """Verify security actions are defined"""
        assert AuditAction.RATE_LIMIT_EXCEEDED.value == "rate_limit_exceeded"
        assert AuditAction.ACCESS_DENIED.value == "access_denied"
        assert AuditAction.USER_ISOLATION_VIOLATION.value == "user_isolation_violation"


class TestAuditLogger:
    """Test AuditLogger class"""

    def test_logger_initialization(self):
        """Test logger initializes correctly"""
        logger = AuditLogger()
        assert logger.db_logging_enabled is False  # Default without env var

    def test_log_creates_record(self, caplog):
        """Test logging creates proper record"""
        logger = AuditLogger()

        with caplog.at_level(logging.INFO):
            logger.log(
                action=AuditAction.VIEW_ACCOUNTS,
                user_id="test-user",
                resource_type="accounts",
                resource_id="acc-123",
                success=True
            )

        assert "AUDIT" in caplog.text
        assert "view_accounts" in caplog.text
        assert "test-user" in caplog.text

    def test_log_with_request(self, caplog):
        """Test logging with HTTP request context"""
        logger = AuditLogger()

        # Mock Azure Functions request
        mock_request = MagicMock()
        mock_request.headers = {
            "X-Forwarded-For": "192.168.1.1",
            "User-Agent": "TestClient/1.0"
        }
        mock_request.url = "/api/accounts"
        mock_request.method = "GET"

        with caplog.at_level(logging.INFO):
            logger.log(
                action=AuditAction.VIEW_ACCOUNTS,
                user_id="test-user",
                request=mock_request,
                success=True
            )

        assert "AUDIT" in caplog.text

    def test_log_failure_uses_warning(self, caplog):
        """Test failed actions log at warning level"""
        logger = AuditLogger()

        with caplog.at_level(logging.WARNING):
            logger.log(
                action=AuditAction.ACCESS_DENIED,
                user_id="malicious-user",
                success=False
            )

        assert "AUDIT" in caplog.text
        assert "access_denied" in caplog.text

    def test_sanitize_removes_sensitive_fields(self):
        """Test sensitive fields are redacted from audit data"""
        logger = AuditLogger()

        data = {
            "user_id": "user-123",
            "password": "secret123",
            "access_token": "plaid-token-xyz",
            "plaid_access_token": "another-token",
            "api_key": "key-123",
            "normal_field": "visible"
        }

        sanitized = logger._sanitize_for_audit(data)

        assert sanitized["user_id"] == "user-123"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["access_token"] == "[REDACTED]"
        assert sanitized["plaid_access_token"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["normal_field"] == "visible"

    def test_sanitize_handles_nested_dicts(self):
        """Test sanitization works on nested dictionaries"""
        logger = AuditLogger()

        data = {
            "outer": {
                "password": "secret",
                "inner": {
                    "api_key": "key"
                }
            }
        }

        sanitized = logger._sanitize_for_audit(data)

        assert sanitized["outer"]["password"] == "[REDACTED]"
        assert sanitized["outer"]["inner"]["api_key"] == "[REDACTED]"


class TestAuditLoggerConvenienceMethods:
    """Test convenience methods"""

    def test_log_access(self, caplog):
        """Test log_access convenience method"""
        logger = AuditLogger()

        with caplog.at_level(logging.INFO):
            logger.log_access(
                user_id="user-123",
                resource_type="accounts",
                count=5
            )

        assert "AUDIT" in caplog.text
        assert "user-123" in caplog.text

    def test_log_modification(self, caplog):
        """Test log_modification convenience method"""
        logger = AuditLogger()

        with caplog.at_level(logging.INFO):
            logger.log_modification(
                action=AuditAction.DELETE_ACCOUNT,
                user_id="user-123",
                resource_type="account",
                resource_id="acc-456",
                before={"status": "active"},
                after={"status": "deleted"}
            )

        assert "AUDIT" in caplog.text

    def test_log_security_event(self, caplog):
        """Test log_security_event convenience method"""
        logger = AuditLogger()

        with caplog.at_level(logging.WARNING):
            logger.log_security_event(
                action=AuditAction.RATE_LIMIT_EXCEEDED,
                user_id="user-123",
                reason="Too many requests"
            )

        assert "AUDIT" in caplog.text


class TestGlobalAuditFunctions:
    """Test global convenience functions"""

    def test_get_audit_logger_singleton(self):
        """Test get_audit_logger returns singleton"""
        logger1 = get_audit_logger()
        logger2 = get_audit_logger()

        assert logger1 is logger2

    def test_audit_log_function(self, caplog):
        """Test audit_log convenience function"""
        with caplog.at_level(logging.INFO):
            audit_log(
                action=AuditAction.VIEW_TRANSACTIONS,
                user_id="user-456",
                resource_type="transactions"
            )

        assert "AUDIT" in caplog.text

    def test_audit_access_function(self, caplog):
        """Test audit_access convenience function"""
        with caplog.at_level(logging.INFO):
            audit_access(
                user_id="user-789",
                resource_type="balances",
                count=10
            )

        assert "AUDIT" in caplog.text

    def test_audit_security_event_function(self, caplog):
        """Test audit_security_event convenience function"""
        with caplog.at_level(logging.WARNING):
            audit_security_event(
                action=AuditAction.USER_ISOLATION_VIOLATION,
                user_id="attacker",
                reason="Attempted to access another user's data"
            )

        assert "AUDIT" in caplog.text
        assert "attacker" in caplog.text


class TestAuditDbLogging:
    """Test database logging (mocked)"""

    def test_db_logging_disabled_by_default(self):
        """Verify DB logging is disabled by default"""
        logger = AuditLogger()
        assert logger.db_logging_enabled is False

    def test_db_logging_enabled_with_env_var(self):
        """Verify DB logging can be enabled via env var"""
        with patch.dict(os.environ, {"AUDIT_DB_LOGGING": "true"}):
            logger = AuditLogger()
            assert logger.db_logging_enabled is True

    def test_db_logging_failure_does_not_raise(self, caplog):
        """Verify DB logging failure doesn't break the application"""
        with patch.dict(os.environ, {"AUDIT_DB_LOGGING": "true"}):
            logger = AuditLogger()
            logger._db = MagicMock()
            logger._db.get_connection.side_effect = Exception("DB Error")

            # Should not raise
            with caplog.at_level(logging.ERROR):
                logger._log_to_database({"action": "test"})

            # Should log the error
            assert "Failed to write audit log" in caplog.text
