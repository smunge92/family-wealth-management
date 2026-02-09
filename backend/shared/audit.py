"""
Audit logging for tracking data access and modifications.

Provides compliance-ready audit trails for financial data access,
supporting GLBA, SOX, and other regulatory requirements.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import azure.functions as func

logger = logging.getLogger(__name__)


class AuditAction(Enum):
    """Types of auditable actions"""
    # Data Access
    VIEW_ACCOUNTS = "view_accounts"
    VIEW_TRANSACTIONS = "view_transactions"
    VIEW_BALANCES = "view_balances"
    VIEW_FAMILY_MEMBERS = "view_family_members"

    # Data Modification
    CREATE_ACCOUNT = "create_account"
    UPDATE_ACCOUNT = "update_account"
    DELETE_ACCOUNT = "delete_account"
    CREATE_FAMILY_MEMBER = "create_family_member"
    DELETE_FAMILY_MEMBER = "delete_family_member"

    # Plaid Integration
    PLAID_LINK_TOKEN = "plaid_link_token"
    PLAID_TOKEN_EXCHANGE = "plaid_token_exchange"
    PLAID_SYNC = "plaid_sync"

    # AI Insights
    AI_PORTFOLIO_ANALYSIS = "ai_portfolio_analysis"
    AI_SPENDING_ANALYSIS = "ai_spending_analysis"
    AI_RETIREMENT_PLANNING = "ai_retirement_planning"
    AI_HOUSE_AFFORDABILITY = "ai_house_affordability"

    # Authentication
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    AUTH_TOKEN_REFRESH = "auth_token_refresh"

    # Security Events
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    ACCESS_DENIED = "access_denied"
    USER_ISOLATION_VIOLATION = "user_isolation_violation"


class AuditLogger:
    """
    Centralized audit logging for compliance and security.

    Logs are written to:
    1. Application Insights (via standard logger)
    2. Optionally to a database table for long-term retention
    """

    def __init__(self):
        self.db_logging_enabled = os.getenv("AUDIT_DB_LOGGING", "false").lower() == "true"
        self._db = None

    def _get_db(self):
        """Lazy load database manager"""
        if self._db is None and self.db_logging_enabled:
            try:
                from shared.database import get_db_manager
                self._db = get_db_manager()
            except Exception as e:
                logger.warning(f"Failed to initialize audit DB logging: {e}")
                self.db_logging_enabled = False
        return self._db

    def log(
        self,
        action: AuditAction,
        user_id: Optional[str],
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[func.HttpRequest] = None,
        success: bool = True
    ):
        """
        Log an auditable action.

        Args:
            action: The type of action being performed
            user_id: The ID of the user performing the action
            resource_type: Type of resource being accessed (e.g., "account", "transaction")
            resource_id: ID of the specific resource
            details: Additional context about the action
            request: The HTTP request (for extracting IP, user agent, etc.)
            success: Whether the action was successful
        """
        timestamp = datetime.utcnow().isoformat()

        # Build audit record
        audit_record = {
            "timestamp": timestamp,
            "action": action.value,
            "user_id": user_id or "anonymous",
            "resource_type": resource_type,
            "resource_id": resource_id,
            "success": success,
            "details": details or {}
        }

        # Extract request metadata if available
        if request:
            # Note: In production, X-Forwarded-For should be trusted only if
            # coming from a known proxy (Azure Front Door, etc.)
            audit_record["client_ip"] = request.headers.get("X-Forwarded-For", "unknown")
            audit_record["user_agent"] = request.headers.get("User-Agent", "unknown")
            audit_record["request_path"] = request.url
            audit_record["request_method"] = request.method

        # Log to Application Insights via standard logger
        log_level = logging.INFO if success else logging.WARNING
        logger.log(
            log_level,
            f"AUDIT: {action.value} | user={audit_record['user_id']} | "
            f"resource={resource_type}:{resource_id} | success={success}",
            extra={"audit_record": audit_record}
        )

        # Optionally log to database for long-term retention
        if self.db_logging_enabled:
            self._log_to_database(audit_record)

    def _log_to_database(self, audit_record: Dict[str, Any]):
        """Write audit record to database table"""
        try:
            db = self._get_db()
            if not db:
                return

            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO audit_log (
                        timestamp, action, user_id, resource_type, resource_id,
                        success, client_ip, user_agent, request_path, request_method, details
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    audit_record.get("timestamp"),
                    audit_record.get("action"),
                    audit_record.get("user_id"),
                    audit_record.get("resource_type"),
                    audit_record.get("resource_id"),
                    1 if audit_record.get("success") else 0,
                    audit_record.get("client_ip"),
                    audit_record.get("user_agent"),
                    audit_record.get("request_path"),
                    audit_record.get("request_method"),
                    json.dumps(audit_record.get("details", {}))[:4000]
                ))
                conn.commit()
        except Exception as e:
            # Don't fail the request if audit logging fails
            logger.exception("Failed to write audit log to database")

    def log_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        request: Optional[func.HttpRequest] = None,
        count: Optional[int] = None
    ):
        """Convenience method for logging data access"""
        action_map = {
            "accounts": AuditAction.VIEW_ACCOUNTS,
            "transactions": AuditAction.VIEW_TRANSACTIONS,
            "balances": AuditAction.VIEW_BALANCES,
            "family_members": AuditAction.VIEW_FAMILY_MEMBERS,
        }
        action = action_map.get(resource_type, AuditAction.VIEW_ACCOUNTS)

        details = {}
        if count is not None:
            details["records_accessed"] = count

        self.log(
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            request=request,
            success=True
        )

    def log_modification(
        self,
        action: AuditAction,
        user_id: str,
        resource_type: str,
        resource_id: str,
        request: Optional[func.HttpRequest] = None,
        before: Optional[Dict] = None,
        after: Optional[Dict] = None
    ):
        """Convenience method for logging data modifications"""
        details = {}
        if before:
            details["before"] = self._sanitize_for_audit(before)
        if after:
            details["after"] = self._sanitize_for_audit(after)

        self.log(
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            request=request,
            success=True
        )

    def log_security_event(
        self,
        action: AuditAction,
        user_id: Optional[str],
        request: Optional[func.HttpRequest] = None,
        reason: Optional[str] = None
    ):
        """Log security-related events (access denied, rate limits, etc.)"""
        details = {}
        if reason:
            details["reason"] = reason

        self.log(
            action=action,
            user_id=user_id,
            resource_type="security",
            details=details,
            request=request,
            success=False
        )

    def _sanitize_for_audit(self, data: Dict) -> Dict:
        """Remove sensitive fields from audit data"""
        sensitive_fields = [
            "password", "secret", "token", "access_token",
            "plaid_access_token", "encryption_key", "api_key"
        ]

        sanitized = {}
        for key, value in data.items():
            if any(s in key.lower() for s in sensitive_fields):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_for_audit(value)
            else:
                sanitized[key] = value

        return sanitized


# Global audit logger instance
_audit_logger = None


def get_audit_logger() -> AuditLogger:
    """Get or create the audit logger (lazy initialization)"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# Convenience functions
def audit_log(
    action: AuditAction,
    user_id: Optional[str],
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[func.HttpRequest] = None,
    success: bool = True
):
    """Log an auditable action"""
    get_audit_logger().log(action, user_id, resource_type, resource_id, details, request, success)


def audit_access(
    user_id: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    request: Optional[func.HttpRequest] = None,
    count: Optional[int] = None
):
    """Log data access"""
    get_audit_logger().log_access(user_id, resource_type, resource_id, request, count)


def audit_security_event(
    action: AuditAction,
    user_id: Optional[str],
    request: Optional[func.HttpRequest] = None,
    reason: Optional[str] = None
):
    """Log security events"""
    get_audit_logger().log_security_event(action, user_id, request, reason)
