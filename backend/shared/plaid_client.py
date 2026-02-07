"""
Plaid API client wrapper for financial data integration
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid import ApiClient, Configuration, ApiException

logger = logging.getLogger(__name__)


class PlaidClient:
    """Wrapper for Plaid API operations"""

    VALID_ENVIRONMENTS = ["sandbox", "development", "production"]

    def __init__(self):
        self.client_id = os.getenv("PLAID_CLIENT_ID")
        self.secret = os.getenv("PLAID_SECRET")
        self.env = os.getenv("PLAID_ENV")

        # Validate required configuration - no dangerous defaults
        if not self.client_id:
            raise ValueError("PLAID_CLIENT_ID environment variable is required")
        if not self.secret:
            raise ValueError("PLAID_SECRET environment variable is required")
        if not self.env:
            raise ValueError("PLAID_ENV environment variable is required (sandbox, development, or production)")
        if self.env not in self.VALID_ENVIRONMENTS:
            raise ValueError(f"Invalid PLAID_ENV: {self.env}. Must be one of: {', '.join(self.VALID_ENVIRONMENTS)}")

        # Configure Plaid client
        configuration = Configuration(
            host=self._get_plaid_host(),
            api_key={
                "clientId": self.client_id,
                "secret": self.secret,
            }
        )

        api_client = ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)

    def _get_plaid_host(self) -> str:
        """Get Plaid API host based on environment"""
        hosts = {
            "sandbox": "https://sandbox.plaid.com",
            "development": "https://development.plaid.com",
            "production": "https://production.plaid.com",
        }
        return hosts[self.env]  # Will always be valid due to __init__ validation

    def create_link_token(self, user_id: str, user_email: str) -> Dict:
        """
        Create a Link token for Plaid Link initialization

        Args:
            user_id: User's unique identifier
            user_email: User's email address

        Returns:
            Dictionary containing link_token and expiration
        """
        try:
            request = LinkTokenCreateRequest(
                user=LinkTokenCreateRequestUser(client_user_id=user_id),
                client_name="Family Wealth Management",
                products=[Products("transactions"), Products("investments"), Products("liabilities")],
                country_codes=[CountryCode("US"), CountryCode("CA")],
                language="en",
                webhook=os.getenv("PLAID_WEBHOOK_URL", ""),
            )

            response = self.client.link_token_create(request)
            return {
                "link_token": response["link_token"],
                "expiration": str(response["expiration"]),
            }

        except ApiException as e:
            logger.error(f"Error creating link token: {str(e)}")
            raise

    def exchange_public_token(self, public_token: str) -> Dict:
        """
        Exchange public token for access token

        Args:
            public_token: Public token from Plaid Link

        Returns:
            Dictionary containing access_token and item_id
        """
        try:
            request = ItemPublicTokenExchangeRequest(public_token=public_token)
            response = self.client.item_public_token_exchange(request)

            return {
                "access_token": response["access_token"],
                "item_id": response["item_id"],
            }

        except ApiException as e:
            logger.error(f"Error exchanging public token: {str(e)}")
            raise

    def get_accounts(self, access_token: str) -> List[Dict]:
        """
        Get accounts associated with an access token

        Args:
            access_token: Plaid access token

        Returns:
            List of account dictionaries
        """
        try:
            request = AccountsGetRequest(access_token=access_token)
            response = self.client.accounts_get(request)

            accounts = []
            for account in response["accounts"]:
                accounts.append({
                    "account_id": account["account_id"],
                    "name": account["name"],
                    "type": str(account["type"].value) if hasattr(account["type"], 'value') else str(account["type"]),
                    "subtype": str(account["subtype"].value) if account.get("subtype") and hasattr(account["subtype"], 'value') else str(account.get("subtype", "")),
                    "mask": account.get("mask"),
                    "balances": {
                        "current": float(account["balances"].get("current") or 0),
                        "available": float(account["balances"].get("available") or 0),
                        "currency": account["balances"].get("iso_currency_code", "USD"),
                    },
                })

            return accounts

        except ApiException as e:
            logger.error(f"Error getting accounts: {str(e)}")
            raise

    def get_transactions(
        self,
        access_token: str,
        start_date: datetime,
        end_date: datetime,
        account_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Get transactions for a date range (handles pagination)

        Args:
            access_token: Plaid access token
            start_date: Start date for transactions
            end_date: End date for transactions
            account_ids: Optional list of account IDs to filter

        Returns:
            List of transaction dictionaries
        """
        try:
            from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions

            all_transactions = []
            offset = 0
            batch_size = 100

            while True:
                options = TransactionsGetRequestOptions(
                    count=batch_size,
                    offset=offset
                )
                if account_ids:
                    options.account_ids = account_ids

                request = TransactionsGetRequest(
                    access_token=access_token,
                    start_date=start_date.date(),
                    end_date=end_date.date(),
                    options=options
                )

                response = self.client.transactions_get(request)
                total_transactions = response["total_transactions"]

                for txn in response["transactions"]:
                    all_transactions.append({
                        "transaction_id": txn["transaction_id"],
                        "account_id": txn["account_id"],
                        "amount": txn["amount"],
                        "date": txn["date"],
                        "name": txn["name"],
                        "merchant_name": txn.get("merchant_name"),
                        "category": txn.get("category", []),
                        "pending": txn["pending"],
                        "iso_currency_code": txn.get("iso_currency_code", "USD"),
                    })

                logger.info(f"Retrieved {len(all_transactions)} of {total_transactions} transactions")

                # Check if we have all transactions
                if len(all_transactions) >= total_transactions:
                    break

                offset += batch_size

            return all_transactions

        except ApiException as e:
            logger.error(f"Error getting transactions: {str(e)}")
            raise

    def get_historical_transactions(
        self,
        access_token: str,
        years: int = 2
    ) -> List[Dict]:
        """
        Get maximum historical transactions (typically 2 years)

        Args:
            access_token: Plaid access token
            years: Number of years of history to retrieve

        Returns:
            List of transaction dictionaries
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years)

        return self.get_transactions(access_token, start_date, end_date)

    def get_institution_info(self, institution_id: str) -> Dict:
        """
        Get information about a financial institution

        Args:
            institution_id: Plaid institution ID

        Returns:
            Dictionary with institution details
        """
        try:
            request = InstitutionsGetByIdRequest(
                institution_id=institution_id,
                country_codes=[CountryCode("US"), CountryCode("CA")]
            )

            response = self.client.institutions_get_by_id(request)
            institution = response["institution"]

            return {
                "institution_id": institution["institution_id"],
                "name": institution["name"],
                "country_codes": institution.get("country_codes", []),
                "logo": institution.get("logo"),
            }

        except ApiException as e:
            logger.error(f"Error getting institution info: {str(e)}")
            raise

    def sync_transactions(self, access_token: str, cursor: Optional[str] = None) -> Dict:
        """
        Sync transactions using Plaid's incremental sync

        Args:
            access_token: Plaid access token
            cursor: Cursor from previous sync (None or empty string for initial sync)

        Returns:
            Dictionary with added/modified/removed transactions and next cursor
        """
        try:
            # For initial sync, use empty string instead of None
            if cursor is None:
                cursor = ""

            request = TransactionsSyncRequest(
                access_token=access_token,
                cursor=cursor
            )

            response = self.client.transactions_sync(request)

            return {
                "added": [self._format_transaction(t) for t in response.get("added", [])],
                "modified": [self._format_transaction(t) for t in response.get("modified", [])],
                "removed": [t["transaction_id"] for t in response.get("removed", [])],
                "next_cursor": response["next_cursor"],
                "has_more": response["has_more"],
            }

        except ApiException as e:
            logger.error(f"Error syncing transactions: {str(e)}")
            raise

    def _format_transaction(self, txn: Dict) -> Dict:
        """Format transaction from Plaid API response"""
        return {
            "transaction_id": txn["transaction_id"],
            "account_id": txn["account_id"],
            "amount": txn["amount"],
            "date": txn["date"],
            "name": txn["name"],
            "merchant_name": txn.get("merchant_name"),
            "category": txn.get("category", []),
            "pending": txn["pending"],
            "iso_currency_code": txn.get("iso_currency_code", "USD"),
        }

    def rotate_access_token(self, access_token: str) -> Dict:
        """
        Rotate a Plaid access token for security.

        This invalidates the old access token and returns a new one.
        The new token provides the same access as the old one.

        Recommended to rotate tokens:
        - Periodically (e.g., every 90 days)
        - After a security incident
        - When updating security policies

        Args:
            access_token: Current Plaid access token

        Returns:
            Dictionary with new_access_token
        """
        try:
            from plaid.model.item_access_token_invalidate_request import ItemAccessTokenInvalidateRequest

            request = ItemAccessTokenInvalidateRequest(
                access_token=access_token
            )

            response = self.client.item_access_token_invalidate(request)

            logger.info("Access token rotated successfully")

            return {
                "new_access_token": response["new_access_token"],
            }

        except ApiException as e:
            logger.error(f"Error rotating access token: {str(e)}")
            raise

    def get_item(self, access_token: str) -> Dict:
        """
        Get Item information including last update status.

        Useful for monitoring item health and checking if re-authentication is needed.

        Args:
            access_token: Plaid access token

        Returns:
            Dictionary with item information
        """
        try:
            from plaid.model.item_get_request import ItemGetRequest

            request = ItemGetRequest(access_token=access_token)
            response = self.client.item_get(request)

            item = response["item"]
            status = response.get("status", {})

            return {
                "item_id": item["item_id"],
                "institution_id": item.get("institution_id"),
                "webhook": item.get("webhook"),
                "error": item.get("error"),
                "available_products": item.get("available_products", []),
                "billed_products": item.get("billed_products", []),
                "consent_expiration_time": item.get("consent_expiration_time"),
                "update_type": item.get("update_type"),
                "transactions_last_successful_update": status.get("transactions", {}).get("last_successful_update"),
                "transactions_last_failed_update": status.get("transactions", {}).get("last_failed_update"),
            }

        except ApiException as e:
            logger.error(f"Error getting item: {str(e)}")
            raise

    def remove_item(self, access_token: str) -> bool:
        """
        Remove an Item (disconnect a financial institution).

        This permanently deletes the Item and invalidates the access token.
        Use this when a user wants to disconnect their bank account.

        Args:
            access_token: Plaid access token

        Returns:
            True if successful
        """
        try:
            from plaid.model.item_remove_request import ItemRemoveRequest

            request = ItemRemoveRequest(access_token=access_token)
            self.client.item_remove(request)

            logger.info("Item removed successfully")
            return True

        except ApiException as e:
            logger.error(f"Error removing item: {str(e)}")
            raise


# Note: Global instance removed - create PlaidClient when needed
# This ensures environment variables are read at runtime
def get_plaid_client() -> PlaidClient:
    """Get a PlaidClient instance"""
    return PlaidClient()
