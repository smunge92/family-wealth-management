"""
Tests for input validation module
"""

import pytest
from shared.validation import (
    validate_user_id,
    validate_email,
    validate_string,
    validate_integer,
    validate_float,
    validate_age,
    validate_amount,
    validate_percentage,
    validate_risk_tolerance,
    validate_plaid_token,
    validate_request_body,
    sanitize_string
)


class TestValidateUserId:
    """Test user ID validation"""

    def test_valid_user_id(self):
        is_valid, error = validate_user_id("user-123-abc")
        assert is_valid is True
        assert error is None

    def test_valid_uuid_format(self):
        is_valid, error = validate_user_id("550e8400-e29b-41d4-a716-446655440000")
        assert is_valid is True

    def test_none_user_id(self):
        is_valid, error = validate_user_id(None)
        assert is_valid is False
        assert "required" in error.lower()

    def test_empty_user_id(self):
        is_valid, error = validate_user_id("")
        assert is_valid is False
        assert "empty" in error.lower()

    def test_too_long_user_id(self):
        is_valid, error = validate_user_id("a" * 200)
        assert is_valid is False
        assert "length" in error.lower()

    def test_invalid_characters(self):
        is_valid, error = validate_user_id("user<script>alert(1)</script>")
        assert is_valid is False
        assert "invalid" in error.lower()


class TestValidateEmail:
    """Test email validation"""

    def test_valid_email(self):
        is_valid, error = validate_email("user@example.com")
        assert is_valid is True
        assert error is None

    def test_valid_email_with_subdomain(self):
        is_valid, error = validate_email("user@mail.example.co.uk")
        assert is_valid is True

    def test_invalid_email_no_at(self):
        is_valid, error = validate_email("userexample.com")
        assert is_valid is False
        assert "invalid" in error.lower()

    def test_invalid_email_no_domain(self):
        is_valid, error = validate_email("user@")
        assert is_valid is False

    def test_none_email(self):
        is_valid, error = validate_email(None)
        assert is_valid is False
        assert "required" in error.lower()


class TestValidateString:
    """Test string validation"""

    def test_valid_string(self):
        is_valid, error = validate_string("Hello World", "test_field")
        assert is_valid is True

    def test_optional_none(self):
        is_valid, error = validate_string(None, "test_field", required=False)
        assert is_valid is True

    def test_required_none(self):
        is_valid, error = validate_string(None, "test_field", required=True)
        assert is_valid is False
        assert "required" in error.lower()

    def test_max_length_exceeded(self):
        is_valid, error = validate_string("a" * 100, "test_field", max_length=50)
        assert is_valid is False
        assert "length" in error.lower()

    def test_non_string_type(self):
        is_valid, error = validate_string(12345, "test_field")
        assert is_valid is False
        assert "string" in error.lower()


class TestValidateInteger:
    """Test integer validation"""

    def test_valid_integer(self):
        is_valid, error = validate_integer(42, "test_field")
        assert is_valid is True

    def test_valid_min_max(self):
        is_valid, error = validate_integer(50, "test_field", min_value=0, max_value=100)
        assert is_valid is True

    def test_below_min(self):
        is_valid, error = validate_integer(-5, "test_field", min_value=0)
        assert is_valid is False
        assert "at least" in error.lower()

    def test_above_max(self):
        is_valid, error = validate_integer(150, "test_field", max_value=100)
        assert is_valid is False
        assert "at most" in error.lower()

    def test_float_converted(self):
        is_valid, error = validate_integer(42.5, "test_field")
        assert is_valid is True

    def test_boolean_rejected(self):
        is_valid, error = validate_integer(True, "test_field")
        assert is_valid is False


class TestValidateFloat:
    """Test float validation"""

    def test_valid_float(self):
        is_valid, error = validate_float(3.14, "test_field")
        assert is_valid is True

    def test_valid_integer_as_float(self):
        is_valid, error = validate_float(42, "test_field")
        assert is_valid is True

    def test_min_value(self):
        is_valid, error = validate_float(-10.5, "test_field", min_value=0)
        assert is_valid is False

    def test_max_value(self):
        is_valid, error = validate_float(150.5, "test_field", max_value=100)
        assert is_valid is False


class TestValidateAge:
    """Test age validation"""

    def test_valid_age(self):
        is_valid, error = validate_age(35)
        assert is_valid is True

    def test_too_young(self):
        is_valid, error = validate_age(15)
        assert is_valid is False
        assert "at least" in error.lower()

    def test_too_old(self):
        is_valid, error = validate_age(150)
        assert is_valid is False
        assert "at most" in error.lower()

    def test_boundary_min(self):
        is_valid, error = validate_age(18)
        assert is_valid is True

    def test_boundary_max(self):
        is_valid, error = validate_age(120)
        assert is_valid is True


class TestValidateAmount:
    """Test monetary amount validation"""

    def test_valid_amount(self):
        is_valid, error = validate_amount(1000.50)
        assert is_valid is True

    def test_zero_amount(self):
        is_valid, error = validate_amount(0)
        assert is_valid is True

    def test_negative_not_allowed(self):
        is_valid, error = validate_amount(-100)
        assert is_valid is False

    def test_negative_allowed(self):
        is_valid, error = validate_amount(-100, allow_negative=True)
        assert is_valid is True

    def test_huge_amount_rejected(self):
        is_valid, error = validate_amount(999_999_999_999_999)
        assert is_valid is False


class TestValidatePercentage:
    """Test percentage validation"""

    def test_valid_percentage(self):
        is_valid, error = validate_percentage(50.5)
        assert is_valid is True

    def test_zero_percentage(self):
        is_valid, error = validate_percentage(0)
        assert is_valid is True

    def test_hundred_percentage(self):
        is_valid, error = validate_percentage(100)
        assert is_valid is True

    def test_negative_percentage(self):
        is_valid, error = validate_percentage(-5)
        assert is_valid is False

    def test_over_hundred(self):
        is_valid, error = validate_percentage(105)
        assert is_valid is False


class TestValidateRiskTolerance:
    """Test risk tolerance validation"""

    def test_valid_conservative(self):
        is_valid, error = validate_risk_tolerance("conservative")
        assert is_valid is True

    def test_valid_moderate(self):
        is_valid, error = validate_risk_tolerance("moderate")
        assert is_valid is True

    def test_valid_aggressive(self):
        is_valid, error = validate_risk_tolerance("aggressive")
        assert is_valid is True

    def test_none_allowed(self):
        is_valid, error = validate_risk_tolerance(None)
        assert is_valid is True

    def test_invalid_value(self):
        is_valid, error = validate_risk_tolerance("risky")
        assert is_valid is False
        assert "must be one of" in error.lower()


class TestValidatePlaidToken:
    """Test Plaid token validation"""

    def test_valid_token(self):
        is_valid, error = validate_plaid_token("public-sandbox-12345-abcdef")
        assert is_valid is True

    def test_none_token(self):
        is_valid, error = validate_plaid_token(None)
        assert is_valid is False
        assert "required" in error.lower()

    def test_empty_token(self):
        is_valid, error = validate_plaid_token("")
        assert is_valid is False
        assert "empty" in error.lower()

    def test_too_long_token(self):
        is_valid, error = validate_plaid_token("a" * 250)
        assert is_valid is False
        assert "length" in error.lower()


class TestValidateRequestBody:
    """Test schema-based request body validation"""

    def test_valid_request(self):
        schema = {
            "user_id": {"type": "user_id", "required": True},
            "age": {"type": "integer", "required": True, "min": 18, "max": 100},
            "income": {"type": "float", "required": False}
        }
        body = {"user_id": "user-123", "age": 35, "income": 50000.0}

        is_valid, error = validate_request_body(body, schema)
        assert is_valid is True
        assert error is None

    def test_missing_required_field(self):
        schema = {
            "user_id": {"type": "user_id", "required": True}
        }
        body = {}

        is_valid, error = validate_request_body(body, schema)
        assert is_valid is False
        assert "user_id" in error.lower()

    def test_invalid_field_type(self):
        schema = {
            "age": {"type": "integer", "required": True, "min": 0}
        }
        body = {"age": "thirty-five"}

        is_valid, error = validate_request_body(body, schema)
        assert is_valid is False


class TestSanitizeString:
    """Test string sanitization"""

    def test_basic_sanitize(self):
        result = sanitize_string("  hello world  ")
        assert result == "hello world"

    def test_truncate_long_string(self):
        result = sanitize_string("a" * 1000, max_length=50)
        assert len(result) == 50

    def test_none_returns_none(self):
        result = sanitize_string(None)
        assert result is None

    def test_non_string_converted(self):
        result = sanitize_string(12345)
        assert result == "12345"
