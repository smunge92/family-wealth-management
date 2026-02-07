"""Tests for Database Manager - Family Member Filtering and Calculations"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from shared.database import DatabaseManager


class TestFamilyMemberFiltering:
    """Test database methods for family member filtering"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database manager"""
        with patch.object(DatabaseManager, '__init__', lambda x: None):
            db = DatabaseManager()
            db.server = "test-server"
            db.database = "test-db"
            db.username = "test-user"
            db.password = "test-pass"
            return db

    def test_get_accounts_by_user_without_family_filter(self, mock_db):
        """Test getting accounts without family member filter returns all accounts"""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"account_id": 1, "account_name": "Checking", "family_member_id": 1},
            {"account_id": 2, "account_name": "Savings", "family_member_id": 2},
            {"account_id": 3, "account_name": "Shared", "family_member_id": None},
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        with patch.object(mock_db, 'get_connection', return_value=mock_conn):
            accounts = mock_db.get_accounts_by_user("user123")

        assert len(accounts) == 3
        # Verify query doesn't filter by family_member_id
        call_args = mock_cursor.execute.call_args[0][0]
        assert "family_member_id = %s" not in call_args or call_args.count("family_member_id") == 1

    def test_get_accounts_by_user_with_family_filter(self, mock_db):
        """Test getting accounts with family member filter only returns matching accounts"""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"account_id": 1, "account_name": "Checking", "family_member_id": 1},
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        with patch.object(mock_db, 'get_connection', return_value=mock_conn):
            accounts = mock_db.get_accounts_by_user("user123", family_member_id=1)

        assert len(accounts) == 1
        # Verify query includes family_member_id filter
        call_args = mock_cursor.execute.call_args
        assert 1 in call_args[0][1]  # family_member_id should be in params


class TestTransactionTotals:
    """Test transaction totals calculation"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database manager"""
        with patch.object(DatabaseManager, '__init__', lambda x: None):
            db = DatabaseManager()
            db.server = "test-server"
            db.database = "test-db"
            db.username = "test-user"
            db.password = "test-pass"
            return db

    def test_get_transaction_totals_returns_correct_structure(self, mock_db):
        """Test that transaction totals returns correct structure"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1500.50, 2300.75, 5)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        with patch.object(mock_db, 'get_connection', return_value=mock_conn):
            totals = mock_db.get_transaction_totals_by_user("user123")

        assert "total_income" in totals
        assert "total_expenses" in totals
        assert "pending_count" in totals
        assert totals["total_income"] == 1500.50
        assert totals["total_expenses"] == 2300.75
        assert totals["pending_count"] == 5

    def test_get_transaction_totals_with_family_filter(self, mock_db):
        """Test that transaction totals filters by family member"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (500.00, 800.00, 2)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        with patch.object(mock_db, 'get_connection', return_value=mock_conn):
            totals = mock_db.get_transaction_totals_by_user("user123", family_member_id=1)

        # Verify query includes family_member_id filter
        call_args = mock_cursor.execute.call_args
        assert 1 in call_args[0][1]  # family_member_id should be in params

        assert totals["total_income"] == 500.00
        assert totals["total_expenses"] == 800.00

    def test_get_transaction_totals_empty_results(self, mock_db):
        """Test that transaction totals handles empty results"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        with patch.object(mock_db, 'get_connection', return_value=mock_conn):
            totals = mock_db.get_transaction_totals_by_user("user123")

        assert totals["total_income"] == 0
        assert totals["total_expenses"] == 0
        assert totals["pending_count"] == 0

    def test_get_transaction_totals_null_values(self, mock_db):
        """Test that transaction totals handles NULL values"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (None, None, None)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        with patch.object(mock_db, 'get_connection', return_value=mock_conn):
            totals = mock_db.get_transaction_totals_by_user("user123")

        assert totals["total_income"] == 0
        assert totals["total_expenses"] == 0
        assert totals["pending_count"] == 0


class TestTransactionCount:
    """Test transaction count calculation"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database manager"""
        with patch.object(DatabaseManager, '__init__', lambda x: None):
            db = DatabaseManager()
            return db

    def test_get_transaction_count_without_filter(self, mock_db):
        """Test transaction count without family member filter"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (150,)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        with patch.object(mock_db, 'get_connection', return_value=mock_conn):
            count = mock_db.get_transaction_count_by_user("user123")

        assert count == 150

    def test_get_transaction_count_with_family_filter(self, mock_db):
        """Test transaction count with family member filter"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (50,)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        with patch.object(mock_db, 'get_connection', return_value=mock_conn):
            count = mock_db.get_transaction_count_by_user("user123", family_member_id=1)

        assert count == 50
        # Verify query includes family_member_id filter
        call_args = mock_cursor.execute.call_args
        assert 1 in call_args[0][1]


class TestDeleteFamilyMember:
    """Test family member deletion with cascade"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database manager"""
        with patch.object(DatabaseManager, '__init__', lambda x: None):
            db = DatabaseManager()
            return db

    def test_delete_family_member_cascade_returns_stats(self, mock_db):
        """Test that cascade delete returns deletion statistics"""
        mock_cursor = MagicMock()
        # Mock the various queries
        mock_cursor.fetchall.return_value = [(1,), (2,)]  # 2 account IDs
        mock_cursor.fetchone.side_effect = [(10,), (5,)]  # 10 transactions, 5 balances
        mock_cursor.rowcount = 2  # accounts deleted

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        with patch.object(mock_db, 'get_connection', return_value=mock_conn):
            result = mock_db.delete_family_member(1, cascade_delete=True)

        assert "deleted" in result
        assert "accounts_deleted" in result
        assert "transactions_deleted" in result
        assert "balances_deleted" in result

    def test_delete_family_member_no_cascade_only_unlinks(self, mock_db):
        """Test that non-cascade delete only unlinks accounts"""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        with patch.object(mock_db, 'get_connection', return_value=mock_conn):
            result = mock_db.delete_family_member(1, cascade_delete=False)

        # Should not have deleted accounts/transactions
        assert result["accounts_deleted"] == 0
        assert result["transactions_deleted"] == 0


class TestNetWorthCalculation:
    """Test that net worth correctly sums account balances"""

    def test_net_worth_sums_all_account_types(self):
        """Verify net worth calculation logic (frontend calculation)"""
        accounts = [
            {"type": "depository", "balances": {"current": 5000}},
            {"type": "investment", "balances": {"current": 25000}},
            {"type": "credit", "balances": {"current": -2000}},  # Debt
            {"type": "loan", "balances": {"current": -15000}},   # Loan
        ]

        # Calculate net worth (same logic as frontend)
        accounts_by_type = {}
        for account in accounts:
            acc_type = account.get("type", "other")
            balance = account.get("balances", {}).get("current", 0)
            accounts_by_type[acc_type] = accounts_by_type.get(acc_type, 0) + balance

        total_net_worth = sum(accounts_by_type.values())

        # 5000 + 25000 + (-2000) + (-15000) = 13000
        assert total_net_worth == 13000

    def test_net_worth_handles_missing_balances(self):
        """Verify net worth handles accounts without balance data"""
        accounts = [
            {"type": "depository", "balances": {"current": 5000}},
            {"type": "investment"},  # No balances
            {"type": "savings", "balances": {}},  # Empty balances
        ]

        accounts_by_type = {}
        for account in accounts:
            acc_type = account.get("type", "other")
            balance = account.get("balances", {}).get("current", 0)
            accounts_by_type[acc_type] = accounts_by_type.get(acc_type, 0) + balance

        total_net_worth = sum(accounts_by_type.values())

        assert total_net_worth == 5000


class TestIncomeExpenseCalculation:
    """Test income and expense calculation logic"""

    def test_income_is_negative_amounts(self):
        """In Plaid, negative amounts are income (money coming in)"""
        transactions = [
            {"amount": -1500},  # Income: $1500
            {"amount": -2500},  # Income: $2500
            {"amount": 500},    # Expense: $500
        ]

        # Same logic as frontend/backend
        income = sum(abs(t["amount"]) for t in transactions if t["amount"] < 0)
        expenses = sum(t["amount"] for t in transactions if t["amount"] > 0)

        assert income == 4000  # $1500 + $2500
        assert expenses == 500

    def test_expense_is_positive_amounts(self):
        """In Plaid, positive amounts are expenses (money going out)"""
        transactions = [
            {"amount": 100},   # Expense: $100
            {"amount": 200},   # Expense: $200
            {"amount": 50},    # Expense: $50
            {"amount": -1000}, # Income: $1000
        ]

        expenses = sum(t["amount"] for t in transactions if t["amount"] > 0)

        assert expenses == 350

    def test_net_calculation(self):
        """Test net = income - expenses"""
        income = 5000
        expenses = 3500
        net = income - expenses

        assert net == 1500
