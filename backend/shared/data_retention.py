"""
Data retention and deletion utilities for compliance.

Supports:
- GDPR right-to-be-forgotten (complete user data deletion)
- Configurable data retention periods
- Transaction archival
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Default retention periods (in days)
DEFAULT_TRANSACTION_RETENTION_DAYS = 730  # 2 years
DEFAULT_AUDIT_LOG_RETENTION_DAYS = 2555  # 7 years (financial compliance)
DEFAULT_SESSION_RETENTION_DAYS = 30


class DataRetentionManager:
    """
    Manages data retention policies and cleanup operations.

    Usage:
        retention = DataRetentionManager()

        # Delete old transactions
        retention.cleanup_old_transactions()

        # Delete a user's data (GDPR)
        retention.delete_user_data("user-123")
    """

    def __init__(self):
        self.transaction_retention_days = int(
            os.getenv("TRANSACTION_RETENTION_DAYS", DEFAULT_TRANSACTION_RETENTION_DAYS)
        )
        self.audit_log_retention_days = int(
            os.getenv("AUDIT_LOG_RETENTION_DAYS", DEFAULT_AUDIT_LOG_RETENTION_DAYS)
        )
        self._db = None

    def _get_db(self):
        """Lazy load database manager"""
        if self._db is None:
            from shared.database import get_db_manager
            self._db = get_db_manager()
        return self._db

    def cleanup_old_transactions(self, older_than_days: Optional[int] = None) -> Dict:
        """
        Delete transactions older than the retention period.

        Args:
            older_than_days: Override default retention period

        Returns:
            Dictionary with deletion statistics
        """
        days = older_than_days or self.transaction_retention_days
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        logger.info(f"Cleaning up transactions older than {cutoff_date.date()}")

        try:
            db = self._get_db()
            with db.get_connection() as conn:
                cursor = conn.cursor()

                # Count transactions to be deleted
                cursor.execute(
                    "SELECT COUNT(*) as count FROM transactions WHERE date < %s",
                    (cutoff_date.date(),)
                )
                count_result = cursor.fetchone()
                count = count_result[0] if count_result else 0

                if count == 0:
                    logger.info("No old transactions to delete")
                    return {"transactions_deleted": 0}

                # Delete old transactions
                cursor.execute(
                    "DELETE FROM transactions WHERE date < %s",
                    (cutoff_date.date(),)
                )
                conn.commit()

                logger.info(f"Deleted {count} old transactions")
                return {"transactions_deleted": count}

        except Exception as e:
            logger.exception("Error cleaning up old transactions")
            raise

    def cleanup_old_audit_logs(self, older_than_days: Optional[int] = None) -> Dict:
        """
        Delete audit logs older than the retention period.

        Note: Audit logs have a longer retention period for compliance.

        Args:
            older_than_days: Override default retention period

        Returns:
            Dictionary with deletion statistics
        """
        days = older_than_days or self.audit_log_retention_days
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        logger.info(f"Cleaning up audit logs older than {cutoff_date.date()}")

        try:
            db = self._get_db()
            with db.get_connection() as conn:
                cursor = conn.cursor()

                # Check if audit_log table exists
                cursor.execute("""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_NAME = 'audit_log'
                """)
                if cursor.fetchone()[0] == 0:
                    logger.info("audit_log table does not exist")
                    return {"audit_logs_deleted": 0}

                # Count logs to be deleted
                cursor.execute(
                    "SELECT COUNT(*) FROM audit_log WHERE timestamp < %s",
                    (cutoff_date,)
                )
                count = cursor.fetchone()[0]

                if count == 0:
                    logger.info("No old audit logs to delete")
                    return {"audit_logs_deleted": 0}

                # Delete old logs
                cursor.execute(
                    "DELETE FROM audit_log WHERE timestamp < %s",
                    (cutoff_date,)
                )
                conn.commit()

                logger.info(f"Deleted {count} old audit logs")
                return {"audit_logs_deleted": count}

        except Exception as e:
            logger.exception("Error cleaning up old audit logs")
            raise

    def delete_user_data(self, user_id: str, include_audit_logs: bool = False) -> Dict:
        """
        Delete all data for a specific user (GDPR right-to-be-forgotten).

        This permanently removes:
        - User account
        - All family members
        - All linked bank accounts
        - All transactions
        - All balances
        - AI insights
        - Optionally: Audit logs (may need to retain for compliance)

        Args:
            user_id: The user ID to delete
            include_audit_logs: Whether to also delete audit logs (default False for compliance)

        Returns:
            Dictionary with deletion statistics
        """
        logger.warning(f"GDPR DELETE: Starting complete data deletion for user {user_id}")

        stats = {
            "user_deleted": False,
            "family_members_deleted": 0,
            "accounts_deleted": 0,
            "transactions_deleted": 0,
            "balances_deleted": 0,
            "insights_deleted": 0,
            "audit_logs_deleted": 0
        }

        try:
            db = self._get_db()
            with db.get_connection() as conn:
                cursor = conn.cursor()

                # 1. Delete transactions (via accounts)
                cursor.execute("""
                    DELETE t FROM transactions t
                    INNER JOIN accounts a ON t.account_id = a.account_id
                    WHERE a.user_id = %s
                """, (user_id,))
                stats["transactions_deleted"] = cursor.rowcount

                # 2. Delete balances (via accounts)
                cursor.execute("""
                    DELETE b FROM account_balances b
                    INNER JOIN accounts a ON b.account_id = a.account_id
                    WHERE a.user_id = %s
                """, (user_id,))
                stats["balances_deleted"] = cursor.rowcount

                # 3. Delete accounts
                cursor.execute(
                    "DELETE FROM accounts WHERE user_id = %s",
                    (user_id,)
                )
                stats["accounts_deleted"] = cursor.rowcount

                # 4. Delete family members
                cursor.execute(
                    "DELETE FROM family_members WHERE user_id = %s",
                    (user_id,)
                )
                stats["family_members_deleted"] = cursor.rowcount

                # 5. Delete AI insights
                cursor.execute(
                    "DELETE FROM ai_insights WHERE user_id = %s",
                    (user_id,)
                )
                stats["insights_deleted"] = cursor.rowcount

                # 6. Optionally delete audit logs
                if include_audit_logs:
                    cursor.execute("""
                        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
                        WHERE TABLE_NAME = 'audit_log'
                    """)
                    if cursor.fetchone()[0] > 0:
                        cursor.execute(
                            "DELETE FROM audit_log WHERE user_id = %s",
                            (user_id,)
                        )
                        stats["audit_logs_deleted"] = cursor.rowcount

                # 7. Delete user
                cursor.execute(
                    "DELETE FROM users WHERE user_id = %s",
                    (user_id,)
                )
                stats["user_deleted"] = cursor.rowcount > 0

                conn.commit()

            logger.warning(
                f"GDPR DELETE COMPLETE for user {user_id}: "
                f"accounts={stats['accounts_deleted']}, "
                f"transactions={stats['transactions_deleted']}, "
                f"family_members={stats['family_members_deleted']}"
            )

            return stats

        except Exception as e:
            logger.exception(f"Error during GDPR delete for user {user_id}")
            raise

    def export_user_data(self, user_id: str) -> Dict:
        """
        Export all data for a user (GDPR data portability).

        Returns:
            Dictionary containing all user data
        """
        logger.info(f"GDPR EXPORT: Exporting data for user {user_id}")

        try:
            db = self._get_db()

            export_data = {
                "export_timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "user": None,
                "family_members": [],
                "accounts": [],
                "transactions": [],
                "insights": []
            }

            with db.get_connection() as conn:
                cursor = conn.cursor(as_dict=True)

                # Get user data
                cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
                user = cursor.fetchone()
                if user:
                    # Remove sensitive fields
                    user.pop("password_hash", None)
                    export_data["user"] = user

                # Get family members
                cursor.execute("SELECT * FROM family_members WHERE user_id = %s", (user_id,))
                export_data["family_members"] = cursor.fetchall()

                # Get accounts (without tokens)
                cursor.execute("""
                    SELECT account_id, account_name, account_type, mask, currency,
                           institution_name, family_member_id, created_at, last_synced_at
                    FROM accounts WHERE user_id = %s
                """, (user_id,))
                export_data["accounts"] = cursor.fetchall()

                # Get transactions
                cursor.execute("""
                    SELECT t.* FROM transactions t
                    INNER JOIN accounts a ON t.account_id = a.account_id
                    WHERE a.user_id = %s
                    ORDER BY t.date DESC
                """, (user_id,))
                export_data["transactions"] = cursor.fetchall()

                # Get AI insights
                cursor.execute(
                    "SELECT * FROM ai_insights WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,)
                )
                export_data["insights"] = cursor.fetchall()

            # Convert datetime objects to strings
            export_data = self._serialize_datetimes(export_data)

            logger.info(f"GDPR EXPORT COMPLETE for user {user_id}")
            return export_data

        except Exception as e:
            logger.exception(f"Error exporting data for user {user_id}")
            raise

    def _serialize_datetimes(self, obj):
        """Recursively convert datetime objects to ISO strings"""
        if isinstance(obj, dict):
            return {k: self._serialize_datetimes(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetimes(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj


# Convenience function
def get_data_retention_manager() -> DataRetentionManager:
    """Get a DataRetentionManager instance"""
    return DataRetentionManager()
