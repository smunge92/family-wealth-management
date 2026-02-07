"""
CSV/OFX/Excel parsing utilities for historical data import
Uses Claude AI for intelligent format detection and categorization
"""

import csv
import logging
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
from ofxparse import OfxParser
from io import StringIO, BytesIO
from .claude_client import claude_client

logger = logging.getLogger(__name__)


class TransactionParser:
    """Parse financial transactions from various file formats"""

    def __init__(self):
        self.supported_formats = ["csv", "ofx", "qfx", "xlsx", "xls"]

    def parse_file(
        self,
        file_content: bytes,
        file_type: str,
        account_id: str
    ) -> List[Dict]:
        """
        Parse financial data file

        Args:
            file_content: Raw file content as bytes
            file_type: File extension (csv, ofx, xlsx, etc.)
            account_id: Account ID for the transactions

        Returns:
            List of parsed transactions
        """
        if file_type.lower() == "csv":
            return self._parse_csv(file_content, account_id)
        elif file_type.lower() in ["ofx", "qfx"]:
            return self._parse_ofx(file_content, account_id)
        elif file_type.lower() in ["xlsx", "xls"]:
            return self._parse_excel(file_content, account_id)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def _parse_csv(self, file_content: bytes, account_id: str) -> List[Dict]:
        """Parse CSV file using Claude for intelligent column mapping"""
        try:
            # Decode content
            text_content = file_content.decode("utf-8")

            # Read first few rows to analyze format
            lines = text_content.split("\n")[:5]
            header_sample = "\n".join(lines)

            # Use Claude to identify column mapping
            column_mapping = self._identify_columns_with_claude(header_sample)

            # Parse full CSV with identified columns
            df = pd.read_csv(StringIO(text_content))

            transactions = []
            for _, row in df.iterrows():
                try:
                    transaction = self._map_row_to_transaction(
                        row, column_mapping, account_id
                    )
                    if transaction:
                        transactions.append(transaction)
                except Exception as e:
                    logger.warning(f"Error parsing row: {str(e)}")
                    continue

            return transactions

        except Exception as e:
            logger.error(f"Error parsing CSV: {str(e)}")
            raise

    def _parse_ofx(self, file_content: bytes, account_id: str) -> List[Dict]:
        """Parse OFX/QFX file"""
        try:
            ofx = OfxParser.parse(BytesIO(file_content))

            transactions = []
            for account in ofx.accounts:
                for txn in account.statement.transactions:
                    transactions.append({
                        "account_id": account_id,
                        "date": txn.date,
                        "amount": float(txn.amount),
                        "description": txn.payee or txn.memo,
                        "transaction_id": txn.id,
                        "pending": False,
                        "currency": "USD",
                        "category": None,  # Will be categorized by Claude later
                    })

            return transactions

        except Exception as e:
            logger.error(f"Error parsing OFX: {str(e)}")
            raise

    def _parse_excel(self, file_content: bytes, account_id: str) -> List[Dict]:
        """Parse Excel file"""
        try:
            # Read Excel file
            df = pd.read_excel(BytesIO(file_content))

            # Get header sample for Claude analysis
            header_sample = df.head().to_string()

            # Use Claude to identify columns
            column_mapping = self._identify_columns_with_claude(header_sample)

            # Parse rows
            transactions = []
            for _, row in df.iterrows():
                try:
                    transaction = self._map_row_to_transaction(
                        row, column_mapping, account_id
                    )
                    if transaction:
                        transactions.append(transaction)
                except Exception as e:
                    logger.warning(f"Error parsing row: {str(e)}")
                    continue

            return transactions

        except Exception as e:
            logger.error(f"Error parsing Excel: {str(e)}")
            raise

    def _identify_columns_with_claude(self, header_sample: str) -> Dict[str, str]:
        """
        Use Claude to intelligently identify column mappings

        Args:
            header_sample: Sample of headers and first few rows

        Returns:
            Dictionary mapping standard fields to actual column names
        """
        prompt = f"""
Analyze this financial data file header and identify which columns correspond to:
- date (transaction date)
- amount (transaction amount)
- description (transaction description/memo)
- balance (optional: account balance after transaction)

Return ONLY a JSON object with the mapping, like:
{{"date": "Date", "amount": "Amount", "description": "Description", "balance": "Balance"}}

File sample:
{header_sample}
"""

        try:
            response = claude_client.client.messages.create(
                model=claude_client.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse JSON response
            import json
            mapping = json.loads(response.content[0].text)
            return mapping

        except Exception as e:
            logger.error(f"Error identifying columns: {str(e)}")
            # Fallback to common column names
            return {
                "date": "Date",
                "amount": "Amount",
                "description": "Description"
            }

    def _map_row_to_transaction(
        self,
        row: pd.Series,
        column_mapping: Dict[str, str],
        account_id: str
    ) -> Optional[Dict]:
        """Map a CSV row to a transaction dictionary"""
        try:
            # Extract values using column mapping
            date_str = str(row[column_mapping.get("date", "Date")])
            amount_str = str(row[column_mapping.get("amount", "Amount")])
            description = str(row[column_mapping.get("description", "Description")])

            # Parse date (try multiple formats)
            date = self._parse_date(date_str)
            if not date:
                return None

            # Parse amount
            amount = self._parse_amount(amount_str)
            if amount is None:
                return None

            return {
                "account_id": account_id,
                "date": date,
                "amount": amount,
                "description": description,
                "pending": False,
                "currency": "USD",  # Default, can be enhanced
                "category": None,  # Will be categorized later
            }

        except Exception as e:
            logger.warning(f"Error mapping row: {str(e)}")
            return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string with multiple format attempts"""
        date_formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
            "%m-%d-%Y",
            "%d-%m-%Y",
            "%b %d, %Y",
            "%B %d, %Y",
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return None

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse amount string, handling various formats"""
        try:
            # Remove currency symbols, commas, spaces
            cleaned = amount_str.replace("$", "").replace(",", "").replace(" ", "")

            # Handle parentheses as negative
            if "(" in cleaned and ")" in cleaned:
                cleaned = "-" + cleaned.replace("(", "").replace(")", "")

            return float(cleaned)

        except ValueError:
            logger.warning(f"Could not parse amount: {amount_str}")
            return None

    def categorize_with_claude(self, transactions: List[Dict]) -> List[Dict]:
        """
        Use Claude to categorize imported transactions

        Args:
            transactions: List of transactions without categories

        Returns:
            List of transactions with categories added
        """
        try:
            # Batch transactions for categorization (max 100 at a time)
            batch_size = 100
            categorized_transactions = []

            for i in range(0, len(transactions), batch_size):
                batch = transactions[i:i + batch_size]
                categorized_batch = claude_client.categorize_transactions(batch)
                categorized_transactions.extend(categorized_batch)

            return categorized_transactions

        except Exception as e:
            logger.error(f"Error categorizing transactions: {str(e)}")
            # Return original transactions without categories
            return transactions


# Global parser instance
transaction_parser = TransactionParser()
