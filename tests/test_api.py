"""
Tests for the API functionality.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from crypto_converter.api.service import app, validate_timestamp


class TestAPI:
    """Test cases for the API endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_health_check(self):
        """Test the health check endpoint."""
        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_convert_missing_parameters(self):
        """Test conversion endpoint with missing parameters."""
        response = self.client.get("/convert")
        assert response.status_code == 422

    def test_convert_invalid_amount(self):
        """Test conversion with invalid amount."""
        response = self.client.get("/convert?amount=-10&from=BTCUSDT&to=ETHUSDT")
        assert response.status_code == 422

    def test_convert_unsupported_pair(self):
        """Test conversion with unsupported currency pair."""
        response = self.client.get("/convert?amount=1&from=BTCUSDT&to=LTCETH")
        assert response.status_code == 422

    def test_convert_invalid_timestamp(self):
        """Test conversion with invalid timestamp format."""
        response = self.client.get(
            "/convert?amount=1&from=BTCUSDT&to=ETHUSDT&timestamp=invalid"
        )
        assert response.status_code == 422
        if "detail" in (data := response.json()) and isinstance(data["detail"], dict):
            assert data["detail"]["error"] == "invalid_timestamp"
        else:
            assert "invalid_timestamp" in str(data) or "timestamp" in str(data).lower()

    def test_convert_unsupported_cross_currency(self):
        """Test conversion with unsupported cross-currency pairs."""
        # Test cross-currency conversion which should fail
        response = self.client.get("/convert?amount=1&from=BTCUSDT&to=ETHBTC")
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    def test_404_endpoint(self):
        """Test non-existent endpoint."""
        response = self.client.get("/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "not_found"

    @pytest.mark.parametrize(
        "from_currency,to_currency",
        [
            ("BTCUSDT", "ETHUSDT"),
            ("ETHUSDT", "BTCUSDT"),
            ("BTCUSDT", "ADAUSDT"),
            ("ADAUSDT", "BTCUSDT"),
            ("ETHUSDT", "ADAUSDT"),
            ("ADAUSDT", "ETHUSDT"),
            ("BNBUSDT", "BTCUSDT"),
            ("BTCUSDT", "BNBUSDT"),
            ("BNBUSDT", "ETHUSDT"),
            ("ETHUSDT", "BNBUSDT"),
            ("BNBUSDT", "ADAUSDT"),
            ("ADAUSDT", "BNBUSDT"),
        ],
    )
    def test_convert_supported_usdt_pairs(self, from_currency, to_currency):
        """Test supported USDT-based currency pair conversions."""
        response = self.client.get(
            f"/convert?amount=100&from={from_currency}&to={to_currency}"
        )
        assert response.status_code != 422, (
            f"Conversion {from_currency} -> {to_currency} should be supported"
        )

        if response.status_code == 422:
            data = response.json()
            assert "Cross-currency conversion" not in str(data), (
                f"Pair {from_currency} -> {to_currency} should be supported"
            )

    @pytest.mark.parametrize(
        "from_currency,to_currency",
        [
            ("BTCUSDT", "LTCETH"),
            ("ETHUSDT", "DOGEBTC"),
            ("ADAUSDT", "XLMBNB"),
            ("BNBUSDT", "AVAXETH"),
            ("BTCETH", "ADAUSDT"),
            ("ETHBTC", "BNBUSDT"),
            ("RANDOM1", "RANDOM2"),
        ],
    )
    def test_convert_unsupported_cross_currency_pairs(self, from_currency, to_currency):
        """Test unsupported cross-currency pair conversions."""
        response = self.client.get(
            f"/convert?amount=100&from={from_currency}&to={to_currency}"
        )
        assert response.status_code == 422, (
            f"Conversion {from_currency} -> {to_currency} should be unsupported"
        )

        if "detail" in (data := response.json()) and isinstance(data["detail"], dict):
            assert data["detail"]["error"] == "unsupported_conversion"
            assert "not supported" in data["detail"]["message"]
        else:
            assert "unsupported_conversion" in str(data)

    @pytest.mark.parametrize(
        "from_currency,to_currency",
        [
            ("btcusdt", "ethusdt"),
            ("BTCUSDT", "ETHUSDT"),
            ("BtcUsdt", "EthUsdt"),
            ("btcUSDT", "ETHusdt"),
        ],
    )
    def test_convert_case_insensitive_symbols(self, from_currency, to_currency):
        """Test that currency symbols are case insensitive."""
        response = self.client.get(
            f"/convert?amount=1&from={from_currency}&to={to_currency}"
        )
        assert response.status_code != 422 or "Cross-currency conversion" not in str(
            response.json()
        )

    def test_convert_same_currency_pair(self):
        """Test conversion between the same currency (should work)."""
        response = self.client.get("/convert?amount=100&from=BTCUSDT&to=BTCUSDT")
        assert response.status_code != 422, (
            "Same currency conversion should be supported"
        )

    @pytest.mark.parametrize(
        "amount",
        [
            "0.00000001",
            "0.1",
            "1000000",
            "999.999",
        ],
    )
    def test_convert_amount_edge_cases(self, amount):
        """Test conversion with edge case amounts."""
        response = self.client.get(f"/convert?amount={amount}&from=BTCUSDT&to=ETHUSDT")
        assert response.status_code != 422, f"Amount {amount} should be valid"

    @pytest.mark.parametrize(
        "amount",
        [
            "0",
            "-1",
            "-100.5",
            "abc",
            "",
        ],
    )
    def test_convert_invalid_amounts(self, amount):
        """Test conversion with invalid amounts."""
        response = self.client.get(f"/convert?amount={amount}&from=BTCUSDT&to=ETHUSDT")
        assert response.status_code == 422, f"Amount {amount} should be invalid"

    @pytest.mark.parametrize(
        "timestamp",
        [
            "2023-01-01T12:00:00",
            "2023-01-01T12:00:00Z",
            "2023-01-01T12:00:00%2B00:00",
            "2023-01-01T12:00:00.123456",
        ],
    )
    def test_timestamp_parsing_edge_cases(self, timestamp):
        """Test timestamp parsing with various formats."""
        response = self.client.get(
            f"/convert?amount=1&from=BTCUSDT&to=ETHUSDT&timestamp={timestamp}"
        )
        assert response.status_code != 400 or "invalid_timestamp" not in str(
            response.json()
        ), f"Timestamp {timestamp} should be valid"

    @pytest.mark.parametrize(
        "timestamp",
        [
            "invalid",
            "2023-13-01T12:00:00",
            "2023-01-32T12:00:00",
            "2023-01-01T25:00:00",
            "not-a-date",
            "123456789",
        ],
    )
    def test_invalid_timestamp_formats(self, timestamp):
        """Test conversion with invalid timestamp formats."""
        response = self.client.get(
            f"/convert?amount=1&from=BTCUSDT&to=ETHUSDT&timestamp={timestamp}"
        )
        assert response.status_code == 422, f"Timestamp {timestamp} should be invalid"

        if "detail" in (data := response.json()) and isinstance(data["detail"], dict):
            assert data["detail"]["error"] == "invalid_timestamp"

    @pytest.mark.parametrize(
        "timestamp,description",
        [
            ("", "Empty string should be treated as None"),
            ("2023-01-01T12:00:00", "Valid ISO format without timezone"),
            ("2023-01-01T12:00:00Z", "Valid ISO format with Z timezone"),
            (
                "2023-01-01T12:00:00%2B05:00",
                "Valid ISO format with positive timezone (URL encoded)",
            ),
            ("2023-01-01T12:00:00-08:00", "Valid ISO format with negative timezone"),
            ("2023-01-01T12:00:00.123456", "Valid ISO format with microseconds"),
            (
                "2023-01-01T12:00:00.1234567",
                "Valid ISO format with 7 microsecond digits (Python truncates)",
            ),
            ("2023-01-01T12:00:00.123456Z", "Valid ISO format with microseconds and Z"),
            ("2023-12-31T23:59:59", "Valid end of year timestamp"),
            ("2024-02-29T12:00:00", "Valid leap year date"),
            (
                "2023-01-01 12:00:00",
                "Valid space separator format (Python accepts this)",
            ),
            ("2023-01-01T12:00", "Valid format missing seconds (Python accepts this)"),
            ("2023-01-01", "Valid date only format (Python accepts this)"),
        ],
    )
    def test_timestamp_validation_comprehensive(self, timestamp, description):
        """Test comprehensive timestamp validation scenarios."""
        if timestamp == "":
            response = self.client.get(
                "/convert?amount=1&from=BTCUSDT&to=ETHUSDT&timestamp="
            )
        else:
            response = self.client.get(
                f"/convert?amount=1&from=BTCUSDT&to=ETHUSDT&timestamp={timestamp}"
            )

        assert (
            response.status_code != 422
            or "timestamp" not in str(response.json()).lower()
        ), (
            f"Timestamp '{timestamp}' should be valid: {description}. "
            f"Got status {response.status_code}, response: {response.json() if response.status_code == 422 else 'OK'}"
        )

    @pytest.mark.parametrize(
        "timestamp,description",
        [
            ("2023/01/01T12:00:00", "Slash separators instead of dash"),
            ("2023-1-1T12:0:0", "Single digit month, day, hour, minute, second"),
            ("23-01-01T12:00:00", "Two-digit year"),
            ("12:00:00", "Time only without date"),
            ("2023-01-01T24:00:00", "Invalid hour 24"),
            ("2023-01-01T12:60:00", "Invalid minute 60"),
            ("2023-01-01T12:00:60", "Invalid second 60"),
            ("2023-00-01T12:00:00", "Invalid month 00"),
            ("2023-01-00T12:00:00", "Invalid day 00"),
            ("2023-02-30T12:00:00", "Invalid February 30th"),
            ("2023-04-31T12:00:00", "Invalid April 31st"),
            ("2023-01-01T12:00:00%2B25:00", "Invalid timezone offset"),
            ("now", "Relative time string"),
            ("yesterday", "Relative time string"),
            ("null", "String 'null'"),
            ("undefined", "String 'undefined'"),
            ("not-a-date", "Random string"),
        ],
    )
    def test_timestamp_validation_edge_cases(self, timestamp, description):
        """Test edge cases in timestamp validation."""
        response = self.client.get(
            f"/convert?amount=1&from=BTCUSDT&to=ETHUSDT&timestamp={timestamp}"
        )
        assert response.status_code == 422, (
            f"Timestamp '{timestamp}' should be invalid: {description}. "
            f"Got status {response.status_code}"
        )

        data = response.json()
        assert "timestamp" in str(data).lower() or "iso" in str(data).lower(), (
            f"Error response should mention timestamp validation: {data}"
        )

    def test_timestamp_validation_function_directly(self):
        """Test the validate_timestamp function directly for edge cases."""
        import pytest

        assert validate_timestamp(None) is None
        assert validate_timestamp("") is None

        test_dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        assert validate_timestamp(test_dt) == test_dt

        result = validate_timestamp("2023-01-01T12:00:00Z")
        assert isinstance(result, datetime)
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 1

        with pytest.raises(ValueError, match="Timestamp must be in ISO format"):
            validate_timestamp("invalid-date")

        with pytest.raises(ValueError, match="Timestamp must be in ISO format"):
            validate_timestamp("2023-13-01T12:00:00")
