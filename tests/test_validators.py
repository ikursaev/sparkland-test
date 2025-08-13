"""
Tests for the validators module.
"""

from datetime import datetime

import pytest
from fastapi import HTTPException

from crypto_converter.api.validators import (
    validate_same_base_currencies,
    validate_timestamp,
)


class TestValidators:
    """Test cases for validation functions."""

    @pytest.mark.parametrize(
        "from_currency,to_currency",
        [
            ("BTCUSDT", "ETHUSDT"),
            ("ETHUSDT", "ADAUSDT"),
            ("ETHBTC", "ADABTC"),
            ("ADAETH", "BNBETH"),
            ("BTCBNB", "ETHBNB"),
            ("BTCUSDC", "ETHUSDC"),
            ("BTCUSDT", "BTCUSDT"),
        ],
    )
    def test_validate_same_base_currencies_valid_pairs(
        self, from_currency, to_currency
    ):
        """Test validation for valid same-base currency pairs."""
        assert validate_same_base_currencies(from_currency, to_currency) is None, (
            f"Should be valid: {from_currency} -> {to_currency}"
        )

    @pytest.mark.parametrize(
        "from_currency,to_currency",
        [
            ("BTCUSDT", "ETHBTC"),
            ("ETHUSDT", "ADABTC"),
            ("BTCETH", "ADAUSDT"),
            ("BNBUSDT", "ETHBNB"),
            ("BTCUSDC", "ETHUSDT"),
            ("INVALID", "SYMBOLS"),
            ("BTC", "ETH"),
        ],
    )
    def test_validate_same_base_currencies_invalid_pairs(
        self, from_currency, to_currency
    ):
        """Test validation for invalid cross-base currency pairs."""
        with pytest.raises(HTTPException):
            validate_same_base_currencies(from_currency, to_currency)

    def test_validate_conversion_pair_failure(self):
        """Test that invalid pairs raise HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            validate_same_base_currencies("BTCUSDT", "ETHBTC")

        assert exc_info.value.status_code == 422
        detail = exc_info.value.detail
        assert isinstance(detail, dict)
        assert detail.get("error") == "unsupported_conversion"
        assert "Cross-currency conversion" in detail.get("message", "")

    @pytest.mark.parametrize(
        "from_currency,to_currency,description",
        [
            ("BTCUSDT", "ETHUSDT", "USDT base"),
            ("ETHBTC", "ADABTC", "BTC base"),
            ("BNBETH", "LINKETH", "ETH base"),
            ("DOGEUSDC", "MATICUSDC", "USDC base"),
            ("ATOMCAKE", "INJCAKE", "CAKE base (custom)"),
            ("XLMBNB", "VETBNB", "BNB base"),
        ],
    )
    def test_dynamic_base_validation_valid_cases(
        self, from_currency, to_currency, description
    ):
        """Test that dynamic base currency validation works for valid cases."""
        # Should not raise any exception
        assert validate_same_base_currencies(from_currency, to_currency) is None

    @pytest.mark.parametrize(
        "from_currency,to_currency,description",
        [
            ("BTCUSDT", "ETHBTC", "Different bases (USDT vs BTC)"),
            ("ADAUSDT", "LINKETH", "Different bases (USDT vs ETH)"),
            ("BNBBTC", "MATICUSDC", "Different bases (BTC vs USDC)"),
        ],
    )
    def test_dynamic_base_validation_invalid_cases(
        self, from_currency, to_currency, description
    ):
        """Test that dynamic base currency validation rejects invalid cases."""
        with pytest.raises(HTTPException):
            validate_same_base_currencies(from_currency, to_currency)


class TestTimestampValidator:
    """Test cases for timestamp validation function."""

    @pytest.mark.parametrize(
        "input_value,expected_result",
        [
            (None, None),
            ("", None),
        ],
    )
    def test_validate_timestamp_none_and_empty(self, input_value, expected_result):
        """Test timestamp validation with None and empty values."""
        assert validate_timestamp(input_value) == expected_result

    def test_validate_timestamp_datetime_passthrough(self):
        """Test timestamp validation with datetime object."""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        assert validate_timestamp(dt) == dt

    @pytest.mark.parametrize(
        "timestamp_str,expected_year,expected_month,expected_day",
        [
            ("2023-01-01T12:00:00Z", 2023, 1, 1),
            ("2023-12-31T23:59:59Z", 2023, 12, 31),
            ("2024-06-15T10:30:45Z", 2024, 6, 15),
            ("2023-01-01T12:00:00+00:00", 2023, 1, 1),
            ("2023-01-01T12:00:00", 2023, 1, 1),
        ],
    )
    def test_validate_timestamp_valid_strings(
        self, timestamp_str, expected_year, expected_month, expected_day
    ):
        """Test timestamp validation with valid ISO format strings."""
        result = validate_timestamp(timestamp_str)
        assert isinstance(result, datetime)
        assert result.year == expected_year
        assert result.month == expected_month
        assert result.day == expected_day

    @pytest.mark.parametrize(
        "invalid_timestamp",
        [
            "invalid-date",
            "2023-13-01T12:00:00Z",  # Invalid month
            "2023-01-32T12:00:00Z",  # Invalid day
            "2023-01-01T25:00:00Z",  # Invalid hour
            "not-a-date-at-all",
            "2023/01/01 12:00:00",  # Wrong format
        ],
    )
    def test_validate_timestamp_invalid_strings(self, invalid_timestamp):
        """Test timestamp validation with invalid strings."""
        with pytest.raises(ValueError, match="Timestamp must be in ISO format"):
            validate_timestamp(invalid_timestamp)
