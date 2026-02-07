"""
Tests for data retention and GDPR compliance module
"""

import os
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from shared.data_retention import (
    DataRetentionManager,
    get_data_retention_manager,
    DEFAULT_TRANSACTION_RETENTION_DAYS,
    DEFAULT_AUDIT_LOG_RETENTION_DAYS
)


class TestDataRetentionManagerInit:
    """Test DataRetentionManager initialization"""

    def test_default_retention_periods(self):
        """Test default retention periods are set"""
        manager = DataRetentionManager()

        assert manager.transaction_retention_days == DEFAULT_TRANSACTION_RETENTION_DAYS
        assert manager.audit_log_retention_days == DEFAULT_AUDIT_LOG_RETENTION_DAYS

    def test_custom_retention_periods(self):
        """Test custom retention periods from env vars"""
        with patch.dict(os.environ, {
            "TRANSACTION_RETENTION_DAYS": "365",
            "AUDIT_LOG_RETENTION_DAYS": "3650"
        }):
            manager = DataRetentionManager()

            assert manager.transaction_retention_days == 365
            assert manager.audit_log_retention_days == 3650

    def test_db_lazy_loaded(self):
        """Test database manager is lazy loaded"""
        manager = DataRetentionManager()
        assert manager._db is None


class TestCleanupOldTransactions:
    """Test transaction cleanup functionality"""

    def test_cleanup_returns_stats(self):
        """Test cleanup returns deletion statistics"""
        manager = DataRetentionManager()

        # Mock database
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [100]  # 100 transactions to delete

        manager._db = mock_db

        result = manager.cleanup_old_transactions()

        assert "transactions_deleted" in result

    def test_cleanup_with_custom_days(self):
        """Test cleanup with custom retention days"""
        manager = DataRetentionManager()

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [0]

        manager._db = mock_db

        result = manager.cleanup_old_transactions(older_than_days=30)

        assert result["transactions_deleted"] == 0


class TestDeleteUserData:
    """Test GDPR delete user data functionality"""

    def test_delete_returns_complete_stats(self):
        """Test delete returns all deletion statistics"""
        manager = DataRetentionManager()

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor

        # Mock rowcount for each delete
        mock_cursor.rowcount = 1

        manager._db = mock_db

        result = manager.delete_user_data("user-123")

        assert "user_deleted" in result
        assert "family_members_deleted" in result
        assert "accounts_deleted" in result
        assert "transactions_deleted" in result
        assert "balances_deleted" in result
        assert "insights_deleted" in result

    def test_delete_without_audit_logs(self):
        """Test delete excludes audit logs by default"""
        manager = DataRetentionManager()

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 0

        manager._db = mock_db

        result = manager.delete_user_data("user-123", include_audit_logs=False)

        # audit_logs_deleted should be 0 when not including audit logs
        assert result["audit_logs_deleted"] == 0


class TestExportUserData:
    """Test GDPR data export functionality"""

    def test_export_returns_all_data_types(self):
        """Test export returns all user data types"""
        manager = DataRetentionManager()

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor

        # Mock user data
        mock_cursor.fetchone.return_value = {"user_id": "user-123", "email": "test@example.com"}
        mock_cursor.fetchall.return_value = []

        manager._db = mock_db

        result = manager.export_user_data("user-123")

        assert "export_timestamp" in result
        assert "user_id" in result
        assert "user" in result
        assert "family_members" in result
        assert "accounts" in result
        assert "transactions" in result
        assert "insights" in result

    def test_export_excludes_sensitive_fields(self):
        """Test export removes password hash"""
        manager = DataRetentionManager()

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor

        # Mock user with password_hash
        user_data = {"user_id": "user-123", "password_hash": "secret_hash"}
        mock_cursor.fetchone.return_value = user_data.copy()
        mock_cursor.fetchall.return_value = []

        manager._db = mock_db

        result = manager.export_user_data("user-123")

        # password_hash should be removed
        assert "password_hash" not in result.get("user", {})


class TestSerializeDatetimes:
    """Test datetime serialization for export"""

    def test_datetime_converted_to_string(self):
        """Test datetime objects are converted to ISO strings"""
        manager = DataRetentionManager()

        now = datetime.utcnow()
        data = {"timestamp": now, "name": "test"}

        result = manager._serialize_datetimes(data)

        assert isinstance(result["timestamp"], str)
        assert result["name"] == "test"

    def test_nested_datetimes_converted(self):
        """Test nested datetime objects are converted"""
        manager = DataRetentionManager()

        now = datetime.utcnow()
        data = {
            "outer": {
                "timestamp": now,
                "inner": {
                    "created_at": now
                }
            }
        }

        result = manager._serialize_datetimes(data)

        assert isinstance(result["outer"]["timestamp"], str)
        assert isinstance(result["outer"]["inner"]["created_at"], str)

    def test_list_datetimes_converted(self):
        """Test datetime objects in lists are converted"""
        manager = DataRetentionManager()

        now = datetime.utcnow()
        data = {"items": [{"timestamp": now}, {"timestamp": now}]}

        result = manager._serialize_datetimes(data)

        assert isinstance(result["items"][0]["timestamp"], str)
        assert isinstance(result["items"][1]["timestamp"], str)


class TestGetDataRetentionManager:
    """Test global convenience function"""

    def test_returns_manager_instance(self):
        """Test get_data_retention_manager returns a manager"""
        manager = get_data_retention_manager()

        assert isinstance(manager, DataRetentionManager)
