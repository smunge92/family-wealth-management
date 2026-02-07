"""
Database connection and utilities for Azure SQL
"""

import os
import logging
import pymssql
from typing import Optional, Dict, List, Any
from contextlib import contextmanager
import uuid
from datetime import datetime
from shared.encryption import encrypt_sensitive_data, decrypt_sensitive_data

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages connections to Azure SQL with TLS encryption"""

    def __init__(self):
        self.server = os.getenv("SQL_SERVER")
        self.database = os.getenv("SQL_DATABASE")
        self.username = os.getenv("SQL_USERNAME")
        self.password = os.getenv("SQL_PASSWORD")

        # Connection security settings
        self.connection_timeout = int(os.getenv("SQL_CONNECTION_TIMEOUT", "30"))
        self.login_timeout = int(os.getenv("SQL_LOGIN_TIMEOUT", "15"))

        # Validate required configuration
        if not all([self.server, self.database, self.username, self.password]):
            missing = []
            if not self.server: missing.append("SQL_SERVER")
            if not self.database: missing.append("SQL_DATABASE")
            if not self.username: missing.append("SQL_USERNAME")
            if not self.password: missing.append("SQL_PASSWORD")
            raise ValueError(f"Missing required database configuration: {', '.join(missing)}")

    def _get_connection(self):
        """
        Create a new database connection with TLS encryption.

        Azure SQL Database requires TLS 1.2+ by default.
        We explicitly enable encryption to ensure secure connections.
        """
        return pymssql.connect(
            server=self.server,
            user=self.username,
            password=self.password,
            database=self.database,
            timeout=self.connection_timeout,
            login_timeout=self.login_timeout,
            tds_version="7.3",  # Use TDS 7.3+ for better security/features
            encryption="require",  # Require TLS encryption for all connections
            appname="FamilyWealthManagement"  # Identify app in SQL logs
        )

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = self._get_connection()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

    # ==================== USER OPERATIONS ====================

    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            return cursor.fetchone()

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            return cursor.fetchone()

    def create_or_update_user(self, user_id: str, email: str, first_name: str = None,
                               last_name: str = None, country: str = "US") -> Dict:
        """Create user if not exists, or update if exists"""
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)

            # Check if user exists
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            existing = cursor.fetchone()

            if existing:
                # Update existing user
                cursor.execute("""
                    UPDATE users
                    SET email = %s, first_name = %s, last_name = %s, country = %s
                    WHERE user_id = %s
                """, (email, first_name, last_name, country, user_id))
                logger.info(f"Updated user: {email}")
            else:
                # Create new user
                cursor.execute("""
                    INSERT INTO users (user_id, email, first_name, last_name, country, created_at)
                    VALUES (%s, %s, %s, %s, %s, GETUTCDATE())
                """, (user_id, email, first_name, last_name, country))
                logger.info(f"Created new user: {email}")

            conn.commit()

            # Return the user
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            return cursor.fetchone()

    # ==================== FAMILY MEMBER OPERATIONS ====================

    def get_family_members_by_user(self, user_id: str) -> List[Dict]:
        """Get all family members for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)
            cursor.execute("""
                SELECT * FROM family_members
                WHERE user_id = %s
                ORDER BY is_primary DESC, first_name ASC
            """, (user_id,))
            return cursor.fetchall()

    def get_family_member(self, family_member_id: int) -> Optional[Dict]:
        """Get family member by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)
            cursor.execute(
                "SELECT * FROM family_members WHERE family_member_id = %s",
                (family_member_id,)
            )
            return cursor.fetchone()

    def create_family_member(self, user_id: str, first_name: str, last_name: str,
                             email: str = None, is_primary: bool = False) -> Dict:
        """Create a new family member"""
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)
            cursor.execute("""
                INSERT INTO family_members (user_id, first_name, last_name, email, is_primary, created_at)
                VALUES (%s, %s, %s, %s, %s, GETUTCDATE())
            """, (user_id, first_name, last_name, email, 1 if is_primary else 0))
            conn.commit()

            # Get the newly created family member
            cursor.execute("""
                SELECT * FROM family_members
                WHERE user_id = %s AND first_name = %s AND last_name = %s
            """, (user_id, first_name, last_name))
            return cursor.fetchone()

    def delete_family_member(self, family_member_id: int, cascade_delete: bool = True) -> dict:
        """
        Delete a family member and optionally cascade delete all related data.

        Args:
            family_member_id: ID of the family member to delete
            cascade_delete: If True, delete all accounts, transactions, and balances.
                           If False, just unlink accounts (set family_member_id to NULL).

        Returns:
            dict with deletion stats: {deleted: bool, accounts_deleted: int, transactions_deleted: int}
        """
        result = {
            "deleted": False,
            "accounts_deleted": 0,
            "transactions_deleted": 0,
            "balances_deleted": 0
        }

        with self.get_connection() as conn:
            cursor = conn.cursor()

            if cascade_delete:
                # Get all account IDs for this family member
                cursor.execute(
                    "SELECT account_id FROM accounts WHERE family_member_id = %s",
                    (family_member_id,)
                )
                account_ids = [row[0] for row in cursor.fetchall()]

                if account_ids:
                    # Count transactions before deletion
                    placeholders = ','.join(['%s'] * len(account_ids))
                    cursor.execute(
                        f"SELECT COUNT(*) FROM transactions WHERE account_id IN ({placeholders})",
                        tuple(account_ids)
                    )
                    result["transactions_deleted"] = cursor.fetchone()[0]

                    # Count balances before deletion
                    cursor.execute(
                        f"SELECT COUNT(*) FROM balances WHERE account_id IN ({placeholders})",
                        tuple(account_ids)
                    )
                    result["balances_deleted"] = cursor.fetchone()[0]

                    # Delete plaid sync cursors
                    cursor.execute(
                        f"DELETE FROM plaid_sync_cursors WHERE account_id IN ({placeholders})",
                        tuple(account_ids)
                    )

                    # Delete transactions (CASCADE should handle this, but explicit is safer)
                    cursor.execute(
                        f"DELETE FROM transactions WHERE account_id IN ({placeholders})",
                        tuple(account_ids)
                    )

                    # Delete balances
                    cursor.execute(
                        f"DELETE FROM balances WHERE account_id IN ({placeholders})",
                        tuple(account_ids)
                    )

                    # Delete accounts
                    cursor.execute(
                        "DELETE FROM accounts WHERE family_member_id = %s",
                        (family_member_id,)
                    )
                    result["accounts_deleted"] = cursor.rowcount
            else:
                # Just unlink accounts from this family member
                cursor.execute(
                    "UPDATE accounts SET family_member_id = NULL WHERE family_member_id = %s",
                    (family_member_id,)
                )

            # Delete the family member
            cursor.execute(
                "DELETE FROM family_members WHERE family_member_id = %s",
                (family_member_id,)
            )
            result["deleted"] = cursor.rowcount > 0

            conn.commit()
            return result

    def update_account_family_member(self, account_id: str, family_member_id: int) -> bool:
        """Update the family member for an account"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE accounts SET family_member_id = %s WHERE account_id = %s",
                (family_member_id, account_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    # ==================== ACCOUNT OPERATIONS ====================

    def get_accounts_by_user(self, user_id: str, family_member_id: int = None) -> List[Dict]:
        """Get all accounts for a user, optionally filtered by family member"""
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)
            if family_member_id is not None:
                cursor.execute("""
                    SELECT a.*, i.name as institution_name, i.logo_url,
                           fm.first_name as family_member_first_name,
                           fm.last_name as family_member_last_name
                    FROM accounts a
                    LEFT JOIN institutions i ON a.institution_id = i.institution_id
                    LEFT JOIN family_members fm ON a.family_member_id = fm.family_member_id
                    WHERE a.user_id = %s AND a.is_active = 1 AND a.family_member_id = %s
                    ORDER BY a.created_at DESC
                """, (user_id, family_member_id))
            else:
                cursor.execute("""
                    SELECT a.*, i.name as institution_name, i.logo_url,
                           fm.first_name as family_member_first_name,
                           fm.last_name as family_member_last_name
                    FROM accounts a
                    LEFT JOIN institutions i ON a.institution_id = i.institution_id
                    LEFT JOIN family_members fm ON a.family_member_id = fm.family_member_id
                    WHERE a.user_id = %s AND a.is_active = 1
                    ORDER BY a.created_at DESC
                """, (user_id,))
            accounts = cursor.fetchall()

            # Decrypt access tokens for each account
            for account in accounts:
                if account.get("plaid_access_token"):
                    account["plaid_access_token"] = decrypt_sensitive_data(account["plaid_access_token"])

            return accounts

    def get_account(self, account_id: str) -> Optional[Dict]:
        """Get account by ID with decrypted access token"""
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)
            cursor.execute("SELECT * FROM accounts WHERE account_id = %s", (account_id,))
            account = cursor.fetchone()
            if account and account.get("plaid_access_token"):
                # Decrypt the access token
                account["plaid_access_token"] = decrypt_sensitive_data(account["plaid_access_token"])
            return account

    def get_account_by_plaid_id(self, plaid_account_id: str) -> Optional[Dict]:
        """Get account by Plaid account ID with decrypted access token"""
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)
            cursor.execute("SELECT * FROM accounts WHERE plaid_account_id = %s", (plaid_account_id,))
            account = cursor.fetchone()
            if account and account.get("plaid_access_token"):
                # Decrypt the access token
                account["plaid_access_token"] = decrypt_sensitive_data(account["plaid_access_token"])
            return account

    def create_account(self, user_id: str, plaid_account_id: str, plaid_access_token: str,
                       account_type: str, account_name: str, mask: str = None,
                       currency: str = "USD", institution_id: int = None,
                       family_member_id: int = None) -> Dict:
        """Create a new account"""
        account_id = str(uuid.uuid4())

        # Encrypt the Plaid access token before storing
        encrypted_token = encrypt_sensitive_data(plaid_access_token) if plaid_access_token else None

        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)

            # Check if account already exists
            cursor.execute("SELECT * FROM accounts WHERE plaid_account_id = %s", (plaid_account_id,))
            existing = cursor.fetchone()

            if existing:
                # Update existing account
                cursor.execute("""
                    UPDATE accounts
                    SET plaid_access_token = %s, account_type = %s, account_name = %s,
                        mask = %s, currency = %s, is_active = 1, last_synced_at = GETUTCDATE(),
                        family_member_id = %s
                    WHERE plaid_account_id = %s
                """, (encrypted_token, account_type, account_name, mask, currency,
                      family_member_id, plaid_account_id))
                logger.info(f"Updated existing account: {account_name}")
                account_id = existing['account_id']
            else:
                # Create new account
                cursor.execute("""
                    INSERT INTO accounts (account_id, user_id, institution_id, plaid_account_id,
                        plaid_access_token, account_type, account_name, mask, currency,
                        is_active, last_synced_at, created_at, family_member_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, GETUTCDATE(), GETUTCDATE(), %s)
                """, (account_id, user_id, institution_id, plaid_account_id, encrypted_token,
                      account_type, account_name, mask, currency, family_member_id))
                logger.info(f"Created new account: {account_name}")

            conn.commit()

            # Return the account (without decrypting the token for security)
            cursor.execute("SELECT * FROM accounts WHERE account_id = %s", (account_id,))
            return cursor.fetchone()

    def get_latest_balances_for_accounts(self, account_ids: List[str]) -> Dict[str, Dict]:
        """Get the latest balance for each account"""
        if not account_ids:
            return {}

        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)
            # Get the latest balance for each account using a subquery
            placeholders = ','.join(['%s'] * len(account_ids))
            cursor.execute(f"""
                SELECT b.account_id, b.current_balance, b.available_balance, b.currency
                FROM balances b
                INNER JOIN (
                    SELECT account_id, MAX(date) as max_date
                    FROM balances
                    WHERE account_id IN ({placeholders})
                    GROUP BY account_id
                ) latest ON b.account_id = latest.account_id AND b.date = latest.max_date
            """, tuple(account_ids))
            results = cursor.fetchall()

            return {
                row["account_id"]: {
                    "current_balance": float(row["current_balance"]) if row["current_balance"] else 0,
                    "available_balance": float(row["available_balance"]) if row["available_balance"] else None,
                    "currency": row["currency"] or "USD"
                }
                for row in results
            }

    def save_balance(self, account_id: str, current_balance: float,
                     available_balance: float = None, currency: str = "USD") -> None:
        """Save a balance snapshot for an account"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if balance for today already exists
            cursor.execute("""
                SELECT balance_id FROM balances
                WHERE account_id = %s AND CAST(date AS DATE) = CAST(GETUTCDATE() AS DATE)
            """, (account_id,))
            existing = cursor.fetchone()

            if existing:
                # Update existing balance
                cursor.execute("""
                    UPDATE balances
                    SET current_balance = %s, available_balance = %s, currency = %s
                    WHERE balance_id = %s
                """, (current_balance, available_balance, currency, existing[0]))
            else:
                # Insert new balance
                cursor.execute("""
                    INSERT INTO balances (account_id, date, current_balance, available_balance,
                        currency, created_at)
                    VALUES (%s, GETUTCDATE(), %s, %s, %s, GETUTCDATE())
                """, (account_id, current_balance, available_balance, currency))

            conn.commit()

    # ==================== TRANSACTION OPERATIONS ====================

    def save_transaction(self, account_id: str, plaid_transaction_id: str, date: str,
                         amount: float, description: str, category: str = None,
                         pending: bool = False, currency: str = "USD",
                         merchant_name: str = None, data_source: str = "plaid") -> Dict:
        """Save a transaction to the database"""
        # Combine merchant_name into description if provided
        full_description = merchant_name if merchant_name else description

        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)

            # Check if transaction already exists (by plaid_transaction_id)
            cursor.execute(
                "SELECT * FROM transactions WHERE plaid_transaction_id = %s",
                (plaid_transaction_id,)
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing transaction
                cursor.execute("""
                    UPDATE transactions
                    SET date = %s, amount = %s, description = %s, category = %s,
                        pending = %s, currency = %s
                    WHERE plaid_transaction_id = %s
                """, (date, amount, full_description, category, 1 if pending else 0,
                      currency, plaid_transaction_id))
                transaction_id = existing['transaction_id']
            else:
                # Generate new transaction_id
                transaction_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO transactions (transaction_id, account_id, plaid_transaction_id,
                        date, amount, description, category, pending, currency,
                        data_source, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, GETUTCDATE())
                """, (transaction_id, account_id, plaid_transaction_id, date, amount,
                      full_description, category, 1 if pending else 0, currency, data_source))

            conn.commit()

            cursor.execute("SELECT * FROM transactions WHERE transaction_id = %s", (transaction_id,))
            return cursor.fetchone()

    def get_transactions_by_account(self, account_id: str, limit: int = 100,
                                     offset: int = 0) -> List[Dict]:
        """Get transactions for an account"""
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)
            cursor.execute("""
                SELECT * FROM transactions
                WHERE account_id = %s
                ORDER BY date DESC
                OFFSET %s ROWS FETCH NEXT %s ROWS ONLY
            """, (account_id, offset, limit))
            return cursor.fetchall()

    def get_transactions_by_user(self, user_id: str, limit: int = 100,
                                  offset: int = 0, family_member_id: int = None) -> List[Dict]:
        """Get all transactions for a user across all accounts, optionally filtered by family member"""
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)
            if family_member_id is not None:
                cursor.execute("""
                    SELECT t.*, a.account_name, a.account_type,
                           fm.first_name as family_member_first_name,
                           fm.last_name as family_member_last_name,
                           c.name as user_category_name, c.icon as user_category_icon,
                           c.color as user_category_color
                    FROM transactions t
                    JOIN accounts a ON t.account_id = a.account_id
                    LEFT JOIN family_members fm ON a.family_member_id = fm.family_member_id
                    LEFT JOIN categories c ON t.user_category_id = c.category_id
                    WHERE a.user_id = %s AND a.is_active = 1 AND a.family_member_id = %s
                    ORDER BY t.date DESC
                    OFFSET %s ROWS FETCH NEXT %s ROWS ONLY
                """, (user_id, family_member_id, offset, limit))
            else:
                cursor.execute("""
                    SELECT t.*, a.account_name, a.account_type,
                           fm.first_name as family_member_first_name,
                           fm.last_name as family_member_last_name,
                           c.name as user_category_name, c.icon as user_category_icon,
                           c.color as user_category_color
                    FROM transactions t
                    JOIN accounts a ON t.account_id = a.account_id
                    LEFT JOIN family_members fm ON a.family_member_id = fm.family_member_id
                    LEFT JOIN categories c ON t.user_category_id = c.category_id
                    WHERE a.user_id = %s AND a.is_active = 1
                    ORDER BY t.date DESC
                    OFFSET %s ROWS FETCH NEXT %s ROWS ONLY
                """, (user_id, offset, limit))
            return cursor.fetchall()

    def get_transaction_count_by_user(self, user_id: str, family_member_id: int = None) -> int:
        """Get total transaction count for a user, optionally filtered by family member"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if family_member_id is not None:
                cursor.execute("""
                    SELECT COUNT(*) FROM transactions t
                    JOIN accounts a ON t.account_id = a.account_id
                    WHERE a.user_id = %s AND a.is_active = 1 AND a.family_member_id = %s
                """, (user_id, family_member_id))
            else:
                cursor.execute("""
                    SELECT COUNT(*) FROM transactions t
                    JOIN accounts a ON t.account_id = a.account_id
                    WHERE a.user_id = %s AND a.is_active = 1
                """, (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 0

    def get_transaction_totals_by_user(self, user_id: str, family_member_id: int = None) -> Dict:
        """
        Get total income and expenses for a user, optionally filtered by family member.
        In Plaid, positive amounts are expenses (money out), negative amounts are income (money in).
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if family_member_id is not None:
                cursor.execute("""
                    SELECT
                        COALESCE(SUM(CASE WHEN t.amount < 0 THEN ABS(t.amount) ELSE 0 END), 0) as total_income,
                        COALESCE(SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END), 0) as total_expenses,
                        COUNT(CASE WHEN t.pending = 1 THEN 1 END) as pending_count
                    FROM transactions t
                    JOIN accounts a ON t.account_id = a.account_id
                    WHERE a.user_id = %s AND a.is_active = 1 AND a.family_member_id = %s
                """, (user_id, family_member_id))
            else:
                cursor.execute("""
                    SELECT
                        COALESCE(SUM(CASE WHEN t.amount < 0 THEN ABS(t.amount) ELSE 0 END), 0) as total_income,
                        COALESCE(SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END), 0) as total_expenses,
                        COUNT(CASE WHEN t.pending = 1 THEN 1 END) as pending_count
                    FROM transactions t
                    JOIN accounts a ON t.account_id = a.account_id
                    WHERE a.user_id = %s AND a.is_active = 1
                """, (user_id,))
            result = cursor.fetchone()
            if result:
                return {
                    "total_income": float(result[0]) if result[0] else 0,
                    "total_expenses": float(result[1]) if result[1] else 0,
                    "pending_count": int(result[2]) if result[2] else 0
                }
            return {"total_income": 0, "total_expenses": 0, "pending_count": 0}

    def delete_transaction(self, plaid_transaction_id: str) -> bool:
        """Delete a transaction by Plaid transaction ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM transactions WHERE plaid_transaction_id = %s",
                (plaid_transaction_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    # ==================== SYNC CURSOR OPERATIONS ====================

    def get_sync_cursor(self, account_id: str) -> Optional[str]:
        """Get the sync cursor for an account"""
        with self.get_connection() as conn:
            db_cursor = conn.cursor(as_dict=True)
            db_cursor.execute(
                "SELECT cursor_value FROM plaid_sync_cursors WHERE account_id = %s",
                (account_id,)
            )
            result = db_cursor.fetchone()
            return result['cursor_value'] if result else None

    def save_sync_cursor(self, account_id: str, cursor_value: str) -> None:
        """Save or update the sync cursor for an account"""
        with self.get_connection() as conn:
            db_cursor = conn.cursor()

            # Check if cursor exists
            db_cursor.execute(
                "SELECT account_id FROM plaid_sync_cursors WHERE account_id = %s",
                (account_id,)
            )
            existing = db_cursor.fetchone()

            if existing:
                db_cursor.execute("""
                    UPDATE plaid_sync_cursors
                    SET cursor_value = %s, last_synced_at = GETUTCDATE()
                    WHERE account_id = %s
                """, (cursor_value, account_id))
            else:
                db_cursor.execute("""
                    INSERT INTO plaid_sync_cursors (account_id, cursor_value, last_synced_at)
                    VALUES (%s, %s, GETUTCDATE())
                """, (account_id, cursor_value))

            conn.commit()

    # ==================== INSTITUTION OPERATIONS ====================

    def get_or_create_institution(self, plaid_institution_id: str, name: str,
                                   country: str = None, logo_url: str = None) -> int:
        """Get or create an institution, return institution_id"""
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)

            # Check if institution exists
            cursor.execute(
                "SELECT institution_id FROM institutions WHERE plaid_institution_id = %s",
                (plaid_institution_id,)
            )
            existing = cursor.fetchone()

            if existing:
                return existing['institution_id']

            # Create new institution
            cursor.execute("""
                INSERT INTO institutions (plaid_institution_id, name, country, logo_url, created_at)
                VALUES (%s, %s, %s, %s, GETUTCDATE())
            """, (plaid_institution_id, name, country, logo_url))
            conn.commit()

            # Get the new institution_id
            cursor.execute(
                "SELECT institution_id FROM institutions WHERE plaid_institution_id = %s",
                (plaid_institution_id,)
            )
            return cursor.fetchone()['institution_id']

    # ==================== CATEGORY OPERATIONS ====================

    def get_categories(self, user_id: str) -> List[Dict]:
        """
        Get all categories available to a user (system categories + user's custom categories).
        System categories (user_id IS NULL) are always included.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)
            cursor.execute("""
                SELECT category_id, user_id, name, icon, color, is_system, display_order, created_at
                FROM categories
                WHERE user_id IS NULL OR user_id = %s
                ORDER BY is_system DESC, display_order ASC, name ASC
            """, (user_id,))
            return cursor.fetchall()

    def get_category(self, category_id: int) -> Optional[Dict]:
        """Get a single category by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)
            cursor.execute(
                "SELECT * FROM categories WHERE category_id = %s",
                (category_id,)
            )
            return cursor.fetchone()

    def create_category(self, user_id: str, name: str, icon: str = None,
                        color: str = None) -> Dict:
        """Create a new user category"""
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)

            # Get max display_order for user's categories
            cursor.execute("""
                SELECT COALESCE(MAX(display_order), 0) + 1 as next_order
                FROM categories WHERE user_id = %s
            """, (user_id,))
            next_order = cursor.fetchone()['next_order']

            cursor.execute("""
                INSERT INTO categories (user_id, name, icon, color, is_system, display_order, created_at)
                VALUES (%s, %s, %s, %s, 0, %s, GETUTCDATE())
            """, (user_id, name, icon, color, next_order))
            conn.commit()

            # Get the newly created category
            cursor.execute("""
                SELECT * FROM categories
                WHERE user_id = %s AND name = %s
            """, (user_id, name))
            return cursor.fetchone()

    def update_category(self, category_id: int, user_id: str, name: str = None,
                        icon: str = None, color: str = None) -> Optional[Dict]:
        """
        Update a user category. Cannot modify system categories.
        Returns None if category doesn't exist or is a system category.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)

            # Check if category exists and belongs to user (not a system category)
            cursor.execute("""
                SELECT * FROM categories
                WHERE category_id = %s AND user_id = %s AND is_system = 0
            """, (category_id, user_id))
            existing = cursor.fetchone()

            if not existing:
                return None

            # Build update query dynamically
            updates = []
            params = []
            if name is not None:
                updates.append("name = %s")
                params.append(name)
            if icon is not None:
                updates.append("icon = %s")
                params.append(icon)
            if color is not None:
                updates.append("color = %s")
                params.append(color)

            if updates:
                params.append(category_id)
                cursor.execute(f"""
                    UPDATE categories
                    SET {', '.join(updates)}
                    WHERE category_id = %s
                """, tuple(params))
                conn.commit()

            # Return updated category
            cursor.execute("SELECT * FROM categories WHERE category_id = %s", (category_id,))
            return cursor.fetchone()

    def delete_category(self, category_id: int, user_id: str) -> bool:
        """
        Delete a user category. Cannot delete system categories.
        Transactions using this category will have user_category_id set to NULL.
        Returns True if deleted, False otherwise.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Verify category belongs to user and is not a system category
            cursor.execute("""
                SELECT category_id FROM categories
                WHERE category_id = %s AND user_id = %s AND is_system = 0
            """, (category_id, user_id))
            if not cursor.fetchone():
                return False

            # Remove category from transactions (set to NULL)
            cursor.execute("""
                UPDATE transactions
                SET user_category_id = NULL, category_source = 'plaid'
                WHERE user_category_id = %s
            """, (category_id,))

            # Delete any rules using this category
            cursor.execute(
                "DELETE FROM category_rules WHERE category_id = %s AND user_id = %s",
                (category_id, user_id)
            )

            # Delete the category
            cursor.execute(
                "DELETE FROM categories WHERE category_id = %s",
                (category_id,)
            )
            conn.commit()
            return True

    # ==================== CATEGORY RULE OPERATIONS ====================

    def get_category_rules(self, user_id: str) -> List[Dict]:
        """
        Get all category rules available to a user (system rules + user's custom rules).
        Includes category information via JOIN.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)
            cursor.execute("""
                SELECT cr.rule_id, cr.user_id, cr.category_id, cr.match_type,
                       cr.match_value, cr.priority, cr.is_system, cr.created_at,
                       c.name as category_name, c.icon as category_icon, c.color as category_color
                FROM category_rules cr
                JOIN categories c ON cr.category_id = c.category_id
                WHERE cr.user_id IS NULL OR cr.user_id = %s
                ORDER BY cr.priority ASC, cr.created_at DESC
            """, (user_id,))
            return cursor.fetchall()

    def get_user_category_rules(self, user_id: str) -> List[Dict]:
        """Get only user-created rules (not system rules)"""
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)
            cursor.execute("""
                SELECT cr.rule_id, cr.user_id, cr.category_id, cr.match_type,
                       cr.match_value, cr.priority, cr.is_system, cr.created_at,
                       c.name as category_name, c.icon as category_icon, c.color as category_color
                FROM category_rules cr
                JOIN categories c ON cr.category_id = c.category_id
                WHERE cr.user_id = %s
                ORDER BY cr.priority ASC, cr.created_at DESC
            """, (user_id,))
            return cursor.fetchall()

    def create_category_rule(self, user_id: str, category_id: int, match_type: str,
                             match_value: str, priority: int = 50) -> Dict:
        """
        Create a new user category rule.
        User rules have priority 50 by default (higher than system rules which are 10-30).
        Lower priority number = applied first.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)

            # Normalize match_value to uppercase for consistent matching
            match_value_normalized = match_value.upper().strip()

            cursor.execute("""
                INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system, created_at)
                VALUES (%s, %s, %s, %s, %s, 0, GETUTCDATE())
            """, (user_id, category_id, match_type, match_value_normalized, priority))
            conn.commit()

            # Get the newly created rule with category info
            cursor.execute("""
                SELECT cr.*, c.name as category_name, c.icon as category_icon, c.color as category_color
                FROM category_rules cr
                JOIN categories c ON cr.category_id = c.category_id
                WHERE cr.user_id = %s AND cr.match_type = %s AND cr.match_value = %s
            """, (user_id, match_type, match_value_normalized))
            return cursor.fetchone()

    def delete_category_rule(self, rule_id: int, user_id: str) -> bool:
        """
        Delete a user category rule. Cannot delete system rules.
        Returns True if deleted, False otherwise.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM category_rules
                WHERE rule_id = %s AND user_id = %s AND is_system = 0
            """, (rule_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def apply_category_rules(self, user_id: str, merchant_name: str = None,
                             description: str = None) -> Optional[int]:
        """
        Find the best matching category rule for a transaction.
        Returns category_id if a rule matches, None otherwise.

        Rule matching priority:
        1. User rules (lower priority number first)
        2. System rules (lower priority number first)

        Match types:
        - 'merchant_contains': case-insensitive match on merchant_name
        - 'description_contains': case-insensitive match on description
        """
        if not merchant_name and not description:
            return None

        # Normalize for matching
        merchant_upper = (merchant_name or '').upper()
        description_upper = (description or '').upper()

        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)

            # Get all applicable rules, ordered by priority (user rules first at same priority)
            cursor.execute("""
                SELECT cr.category_id, cr.match_type, cr.match_value, cr.priority, cr.is_system
                FROM category_rules cr
                WHERE cr.user_id IS NULL OR cr.user_id = %s
                ORDER BY
                    CASE WHEN cr.user_id = %s THEN 0 ELSE 1 END,  -- User rules first
                    cr.priority ASC
            """, (user_id, user_id))

            rules = cursor.fetchall()

            for rule in rules:
                match_value = rule['match_value']
                match_type = rule['match_type']

                if match_type == 'merchant_contains' and merchant_upper:
                    if match_value in merchant_upper:
                        return rule['category_id']
                elif match_type == 'description_contains' and description_upper:
                    if match_value in description_upper:
                        return rule['category_id']

            return None

    def update_transaction_category(self, transaction_id: str, category_id: int,
                                     source: str = 'manual') -> bool:
        """
        Update a transaction's category.

        Args:
            transaction_id: UUID of the transaction
            category_id: ID of the category to assign (or None to clear)
            source: 'plaid', 'rule', or 'manual'

        Returns:
            True if updated, False otherwise
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE transactions
                SET user_category_id = %s, category_source = %s
                WHERE transaction_id = %s
            """, (category_id, source, transaction_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_transaction_by_id(self, transaction_id: str) -> Optional[Dict]:
        """Get a single transaction by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)
            cursor.execute("""
                SELECT t.*, a.account_name, a.account_type, a.user_id,
                       c.name as user_category_name, c.icon as user_category_icon,
                       c.color as user_category_color
                FROM transactions t
                JOIN accounts a ON t.account_id = a.account_id
                LEFT JOIN categories c ON t.user_category_id = c.category_id
                WHERE t.transaction_id = %s
            """, (transaction_id,))
            return cursor.fetchone()

    @staticmethod
    def _escape_like_pattern(value: str) -> str:
        """Escape SQL LIKE wildcard characters (% and _) in user input."""
        return value.replace('%', '[%]').replace('_', '[_]')

    def apply_rule_to_similar_transactions(self, user_id: str, rule_id: int) -> int:
        """
        Apply a rule to all existing matching transactions that don't have a manual category.

        Returns the number of transactions updated.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(as_dict=True)

            # Get the rule details
            cursor.execute("""
                SELECT category_id, match_type, match_value
                FROM category_rules WHERE rule_id = %s
            """, (rule_id,))
            rule = cursor.fetchone()

            if not rule:
                return 0

            category_id = rule['category_id']
            match_type = rule['match_type']
            match_value = rule['match_value']

            # Build the appropriate WHERE clause based on match_type
            if match_type == 'merchant_contains':
                match_clause = "UPPER(t.description) LIKE %s"
            else:  # description_contains
                match_clause = "UPPER(t.description) LIKE %s"

            # Escape LIKE wildcards in user-provided match values
            escaped_value = self._escape_like_pattern(match_value)
            match_pattern = f'%{escaped_value}%'

            # Update transactions that:
            # 1. Belong to user's accounts
            # 2. Match the rule pattern
            # 3. Don't have a manual category override
            cursor.execute(f"""
                UPDATE t
                SET t.user_category_id = %s, t.category_source = 'rule'
                FROM transactions t
                JOIN accounts a ON t.account_id = a.account_id
                WHERE a.user_id = %s
                  AND a.is_active = 1
                  AND (t.category_source IS NULL OR t.category_source != 'manual')
                  AND {match_clause}
            """, (category_id, user_id, match_pattern))

            updated_count = cursor.rowcount
            conn.commit()
            return updated_count

    def count_similar_transactions(self, user_id: str, match_type: str, match_value: str) -> int:
        """
        Count how many transactions would match a rule pattern.
        Used to show "Found X similar transactions" in UI.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Escape LIKE wildcards in user-provided match values
            escaped_value = self._escape_like_pattern(match_value.upper())
            match_pattern = f'%{escaped_value}%'

            cursor.execute("""
                SELECT COUNT(*)
                FROM transactions t
                JOIN accounts a ON t.account_id = a.account_id
                WHERE a.user_id = %s
                  AND a.is_active = 1
                  AND UPPER(t.description) LIKE %s
            """, (user_id, match_pattern))

            result = cursor.fetchone()
            return result[0] if result else 0


# Lazy-loaded database manager instance
_db_manager = None

def get_db_manager() -> DatabaseManager:
    """Get or create the database manager (lazy initialization)"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
