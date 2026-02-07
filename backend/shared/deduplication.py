"""
Transaction deduplication logic to prevent duplicate entries
when importing from multiple sources (Plaid + CSV)
"""

import logging
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class TransactionDeduplicator:
    """Detects and removes duplicate transactions"""

    def __init__(
        self,
        date_tolerance_days: int = 2,
        description_similarity_threshold: float = 0.8
    ):
        """
        Initialize deduplicator

        Args:
            date_tolerance_days: Number of days +/- to consider for date matching
            description_similarity_threshold: Threshold for description similarity (0-1)
        """
        self.date_tolerance = timedelta(days=date_tolerance_days)
        self.similarity_threshold = description_similarity_threshold

    def find_duplicates(
        self,
        new_transactions: List[Dict],
        existing_transactions: List[Dict]
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Find duplicates between new and existing transactions

        Args:
            new_transactions: List of transactions to check
            existing_transactions: List of existing transactions in database

        Returns:
            Tuple of (unique_transactions, duplicate_transactions)
        """
        unique = []
        duplicates = []

        for new_txn in new_transactions:
            is_duplicate = False

            for existing_txn in existing_transactions:
                if self._is_duplicate(new_txn, existing_txn):
                    is_duplicate = True
                    duplicates.append(new_txn)
                    logger.info(
                        f"Found duplicate: {new_txn.get('description')} "
                        f"on {new_txn.get('date')}"
                    )
                    break

            if not is_duplicate:
                unique.append(new_txn)

        logger.info(
            f"Deduplication complete: {len(unique)} unique, "
            f"{len(duplicates)} duplicates found"
        )

        return unique, duplicates

    def _is_duplicate(self, txn1: Dict, txn2: Dict) -> bool:
        """
        Check if two transactions are duplicates

        Matching criteria:
        - Dates within tolerance window
        - Amounts exactly match
        - Descriptions are sufficiently similar
        - Same account (if specified)

        Args:
            txn1: First transaction
            txn2: Second transaction

        Returns:
            True if transactions are duplicates, False otherwise
        """
        # Check account match (if both have account_id)
        if txn1.get("account_id") and txn2.get("account_id"):
            if txn1["account_id"] != txn2["account_id"]:
                return False

        # Check date match (within tolerance)
        if not self._dates_match(txn1.get("date"), txn2.get("date")):
            return False

        # Check amount match (exact)
        if not self._amounts_match(txn1.get("amount"), txn2.get("amount")):
            return False

        # Check description similarity
        if not self._descriptions_similar(
            txn1.get("description", ""),
            txn2.get("description", "")
        ):
            return False

        return True

    def _dates_match(self, date1, date2) -> bool:
        """Check if two dates match within tolerance"""
        if not date1 or not date2:
            return False

        # Convert to datetime if strings
        if isinstance(date1, str):
            date1 = datetime.fromisoformat(date1.replace("Z", "+00:00"))
        if isinstance(date2, str):
            date2 = datetime.fromisoformat(date2.replace("Z", "+00:00"))

        # Check if dates are within tolerance
        diff = abs((date1 - date2).total_seconds())
        return diff <= self.date_tolerance.total_seconds()

    def _amounts_match(self, amount1, amount2) -> bool:
        """Check if two amounts exactly match"""
        if amount1 is None or amount2 is None:
            return False

        # Handle string amounts
        if isinstance(amount1, str):
            amount1 = float(amount1)
        if isinstance(amount2, str):
            amount2 = float(amount2)

        # Exact match with small tolerance for floating point
        return abs(amount1 - amount2) < 0.01

    def _descriptions_similar(self, desc1: str, desc2: str) -> bool:
        """
        Check if two descriptions are similar using sequence matching

        Args:
            desc1: First description
            desc2: Second description

        Returns:
            True if descriptions are similar enough
        """
        if not desc1 or not desc2:
            return False

        # Normalize descriptions (lowercase, strip whitespace)
        desc1 = desc1.lower().strip()
        desc2 = desc2.lower().strip()

        # Calculate similarity ratio
        similarity = SequenceMatcher(None, desc1, desc2).ratio()

        return similarity >= self.similarity_threshold

    def remove_internal_duplicates(
        self,
        transactions: List[Dict]
    ) -> List[Dict]:
        """
        Remove duplicates within a single transaction list

        Args:
            transactions: List of transactions

        Returns:
            List of unique transactions
        """
        unique = []
        seen_signatures = set()

        for txn in transactions:
            signature = self._get_transaction_signature(txn)

            if signature not in seen_signatures:
                unique.append(txn)
                seen_signatures.add(signature)
            else:
                logger.info(f"Removed internal duplicate: {txn.get('description')}")

        logger.info(
            f"Removed {len(transactions) - len(unique)} internal duplicates"
        )

        return unique

    def _get_transaction_signature(self, txn: Dict) -> str:
        """
        Generate a unique signature for a transaction

        Args:
            txn: Transaction dictionary

        Returns:
            Transaction signature string
        """
        date = txn.get("date", "")
        if isinstance(date, datetime):
            date = date.isoformat()

        amount = txn.get("amount", 0)
        description = txn.get("description", "").lower().strip()

        return f"{date}|{amount}|{description}"

    def merge_transaction_data(
        self,
        plaid_txn: Dict,
        csv_txn: Dict
    ) -> Dict:
        """
        Merge data from Plaid and CSV transactions, preferring Plaid data

        Args:
            plaid_txn: Transaction from Plaid
            csv_txn: Transaction from CSV

        Returns:
            Merged transaction dictionary
        """
        merged = plaid_txn.copy()

        # Add CSV-specific data if not in Plaid data
        if not merged.get("description") and csv_txn.get("description"):
            merged["description"] = csv_txn["description"]

        # Add note that this was matched with CSV
        merged["csv_matched"] = True

        return merged


# Global deduplicator instance
deduplicator = TransactionDeduplicator()
