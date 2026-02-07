"""
Input validation utilities for API endpoints.

Provides validation functions for common input types to prevent
injection attacks and ensure data integrity.
"""

import re
import logging
from typing import Optional, Any, Tuple

logger = logging.getLogger(__name__)

# Validation constants
MAX_STRING_LENGTH = 500
MAX_EMAIL_LENGTH = 254
MAX_USER_ID_LENGTH = 128
MIN_AGE = 18
MAX_AGE = 120
MIN_AMOUNT = 0
MAX_AMOUNT = 100_000_000_000  # 100 billion

# Regex patterns
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
UUID_PATTERN = re.compile(r'^[a-zA-Z0-9\-_|]+$')  # Allow common user ID formats
SAFE_STRING_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_.,\'\"()&@#!?]+$')


class ValidationError(Exception):
    """Raised when input validation fails."""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


def validate_user_id(user_id: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate user ID format.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if user_id is None:
        return False, "user_id is required"

    if not isinstance(user_id, str):
        return False, "user_id must be a string"

    user_id = user_id.strip()

    if len(user_id) == 0:
        return False, "user_id cannot be empty"

    if len(user_id) > MAX_USER_ID_LENGTH:
        return False, f"user_id exceeds maximum length of {MAX_USER_ID_LENGTH}"

    if not UUID_PATTERN.match(user_id):
        return False, "user_id contains invalid characters"

    return True, None


def validate_email(email: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate email format.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if email is None:
        return False, "email is required"

    if not isinstance(email, str):
        return False, "email must be a string"

    email = email.strip()

    if len(email) == 0:
        return False, "email cannot be empty"

    if len(email) > MAX_EMAIL_LENGTH:
        return False, f"email exceeds maximum length of {MAX_EMAIL_LENGTH}"

    if not EMAIL_PATTERN.match(email):
        return False, "email format is invalid"

    return True, None


def validate_string(value: Any, field_name: str, required: bool = True,
                   max_length: int = MAX_STRING_LENGTH,
                   allow_special: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Validate a string field.

    Args:
        value: The value to validate
        field_name: Name of the field for error messages
        required: Whether the field is required
        max_length: Maximum allowed length
        allow_special: Whether to allow special characters

    Returns:
        Tuple of (is_valid, error_message)
    """
    if value is None:
        if required:
            return False, f"{field_name} is required"
        return True, None

    if not isinstance(value, str):
        return False, f"{field_name} must be a string"

    value = value.strip()

    if len(value) == 0:
        if required:
            return False, f"{field_name} cannot be empty"
        return True, None

    if len(value) > max_length:
        return False, f"{field_name} exceeds maximum length of {max_length}"

    if not allow_special and not SAFE_STRING_PATTERN.match(value):
        return False, f"{field_name} contains invalid characters"

    return True, None


def validate_integer(value: Any, field_name: str, required: bool = True,
                    min_value: Optional[int] = None,
                    max_value: Optional[int] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate an integer field.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if value is None:
        if required:
            return False, f"{field_name} is required"
        return True, None

    if isinstance(value, bool):  # bool is subclass of int, but we don't want bools
        return False, f"{field_name} must be an integer"

    if not isinstance(value, (int, float)):
        return False, f"{field_name} must be a number"

    try:
        int_value = int(value)
    except (ValueError, OverflowError):
        return False, f"{field_name} must be a valid integer"

    if min_value is not None and int_value < min_value:
        return False, f"{field_name} must be at least {min_value}"

    if max_value is not None and int_value > max_value:
        return False, f"{field_name} must be at most {max_value}"

    return True, None


def validate_float(value: Any, field_name: str, required: bool = True,
                  min_value: Optional[float] = None,
                  max_value: Optional[float] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate a float/decimal field.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if value is None:
        if required:
            return False, f"{field_name} is required"
        return True, None

    if isinstance(value, bool):
        return False, f"{field_name} must be a number"

    if not isinstance(value, (int, float)):
        return False, f"{field_name} must be a number"

    try:
        float_value = float(value)
    except (ValueError, OverflowError):
        return False, f"{field_name} must be a valid number"

    if min_value is not None and float_value < min_value:
        return False, f"{field_name} must be at least {min_value}"

    if max_value is not None and float_value > max_value:
        return False, f"{field_name} must be at most {max_value}"

    return True, None


def validate_age(value: Any, field_name: str = "age",
                required: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Validate an age field (18-120).

    Returns:
        Tuple of (is_valid, error_message)
    """
    return validate_integer(value, field_name, required, MIN_AGE, MAX_AGE)


def validate_amount(value: Any, field_name: str = "amount",
                   required: bool = True,
                   allow_negative: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Validate a monetary amount.

    Returns:
        Tuple of (is_valid, error_message)
    """
    min_val = -MAX_AMOUNT if allow_negative else MIN_AMOUNT
    return validate_float(value, field_name, required, min_val, MAX_AMOUNT)


def validate_percentage(value: Any, field_name: str = "percentage",
                       required: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Validate a percentage (0-100).

    Returns:
        Tuple of (is_valid, error_message)
    """
    return validate_float(value, field_name, required, 0, 100)


def validate_risk_tolerance(value: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate risk tolerance value.

    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_values = ["conservative", "moderate", "aggressive"]

    if value is None:
        return True, None  # Default will be applied

    if not isinstance(value, str):
        return False, "risk_tolerance must be a string"

    if value.lower() not in valid_values:
        return False, f"risk_tolerance must be one of: {', '.join(valid_values)}"

    return True, None


def validate_plaid_token(value: Any, field_name: str = "token") -> Tuple[bool, Optional[str]]:
    """
    Validate a Plaid token (public token, access token, etc.).

    Returns:
        Tuple of (is_valid, error_message)
    """
    if value is None:
        return False, f"{field_name} is required"

    if not isinstance(value, str):
        return False, f"{field_name} must be a string"

    value = value.strip()

    if len(value) == 0:
        return False, f"{field_name} cannot be empty"

    # Plaid tokens are typically alphanumeric with hyphens
    if len(value) > 200:
        return False, f"{field_name} exceeds maximum length"

    return True, None


def sanitize_string(value: Optional[str], max_length: int = MAX_STRING_LENGTH) -> Optional[str]:
    """
    Sanitize a string by trimming and truncating.

    Returns:
        Sanitized string or None
    """
    if value is None:
        return None

    if not isinstance(value, str):
        return str(value)[:max_length]

    return value.strip()[:max_length]


def validate_request_body(body: dict, schema: dict) -> Tuple[bool, Optional[str]]:
    """
    Validate a request body against a schema.

    Schema format:
    {
        "field_name": {
            "type": "string" | "integer" | "float" | "email" | "user_id",
            "required": True | False,
            "min": number (optional),
            "max": number (optional),
            "max_length": number (optional for strings)
        }
    }

    Returns:
        Tuple of (is_valid, error_message)
    """
    for field_name, rules in schema.items():
        value = body.get(field_name)
        field_type = rules.get("type", "string")
        required = rules.get("required", False)

        if field_type == "string":
            is_valid, error = validate_string(
                value, field_name, required,
                rules.get("max_length", MAX_STRING_LENGTH)
            )
        elif field_type == "integer":
            is_valid, error = validate_integer(
                value, field_name, required,
                rules.get("min"), rules.get("max")
            )
        elif field_type == "float":
            is_valid, error = validate_float(
                value, field_name, required,
                rules.get("min"), rules.get("max")
            )
        elif field_type == "email":
            if required or value is not None:
                is_valid, error = validate_email(value)
            else:
                is_valid, error = True, None
        elif field_type == "user_id":
            is_valid, error = validate_user_id(value)
        elif field_type == "amount":
            is_valid, error = validate_amount(
                value, field_name, required,
                rules.get("allow_negative", False)
            )
        elif field_type == "percentage":
            is_valid, error = validate_percentage(value, field_name, required)
        elif field_type == "age":
            is_valid, error = validate_age(value, field_name, required)
        elif field_type == "risk_tolerance":
            is_valid, error = validate_risk_tolerance(value)
        else:
            is_valid, error = True, None

        if not is_valid:
            return False, error

    return True, None
