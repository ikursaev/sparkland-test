"""
Integration tests for the complete system.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestIntegration:
    """Integration tests for the crypto converter system."""

    @pytest.mark.asyncio
    async def test_quote_consumer_parsing_rest(self):
        """Test that quote consumer can parse Binance REST API ticker data."""

        from crypto_converter.quote_consumer.service import QuoteConsumer

        consumer = QuoteConsumer()

        rest_data = {"symbol": "BTCUSDT", "price": "45000.50"}

        timestamp = datetime.now(UTC)
        quote = consumer._parse_binance_rest_ticker(rest_data, timestamp)

        assert quote is not None
        assert quote.symbol == "BTCUSDT"
        assert quote.price == 45000.50
        assert quote.timestamp == timestamp

    @pytest.mark.asyncio
    async def test_quote_consumer_invalid_data(self):
        """Test quote consumer with invalid REST API data."""

        from crypto_converter.quote_consumer.service import QuoteConsumer

        consumer = QuoteConsumer()

        invalid_data = {"invalid": "data"}
        timestamp = datetime.now(UTC)
        quote = consumer._parse_binance_rest_ticker(invalid_data, timestamp)

        assert quote is None

    @pytest.mark.asyncio
    async def test_end_to_end_conversion(self, temp_storage, sample_quotes):
        """Test end-to-end conversion flow."""
        await temp_storage.save_quotes(sample_quotes)

        rate_info = await temp_storage.get_conversion_rate("BTCUSDT", "ETHUSDT")
        assert rate_info is not None
        assert "rate" in rate_info

        expected_rate = 45000.0 / 3000.0
        assert abs(rate_info["rate"] - expected_rate) < 0.001

        amount = 1.0
        converted_amount = amount * rate_info["rate"]
        assert abs(converted_amount - 15.0) < 0.001

    @pytest.mark.asyncio
    async def test_parse_binance_rest_ticker(self):
        """Test parsing Binance REST API ticker data."""

        from crypto_converter.quote_consumer.service import QuoteConsumer

        consumer = QuoteConsumer()

        rest_data = {"symbol": "BTCUSDT", "price": "45000.50"}

        timestamp = datetime.now(UTC)
        quote = consumer._parse_binance_rest_ticker(rest_data, timestamp)

        assert quote is not None
        assert quote.symbol == "BTCUSDT"
        assert quote.price == 45000.50
        assert quote.timestamp == timestamp

    @pytest.mark.asyncio
    async def test_parse_binance_rest_ticker_invalid(self):
        """Test parsing invalid Binance REST API ticker data."""

        from crypto_converter.quote_consumer.service import QuoteConsumer

        consumer = QuoteConsumer()

        invalid_data = {"invalid": "data"}
        timestamp = datetime.now(UTC)
        quote = consumer._parse_binance_rest_ticker(invalid_data, timestamp)

        assert quote is None
