"""
Integration tests for the complete system.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestIntegration:
    """Integration tests for the crypto converter system."""

    @pytest.mark.asyncio
    async def test_quote_consumer_parsing(self):
        """Test that quote consumer can parse Binance ticker data."""
        from crypto_converter.quote_consumer.service import QuoteConsumer

        consumer = QuoteConsumer()

        # Sample Binance ticker message
        sample_data = {
            "s": "BTCUSDT",
            "c": "45000.50",
            "E": int(datetime.now(UTC).timestamp() * 1000),
        }

        quote = consumer._parse_binance_ticker(sample_data)
        assert quote is not None
        assert quote.symbol == "BTCUSDT"
        assert quote.price == 45000.50

    @pytest.mark.asyncio
    async def test_quote_consumer_invalid_data(self):
        """Test quote consumer with invalid data."""
        from crypto_converter.quote_consumer.service import QuoteConsumer

        consumer = QuoteConsumer()

        # Invalid data
        invalid_data = {"invalid": "data"}
        quote = consumer._parse_binance_ticker(invalid_data)
        assert quote is None

    @pytest.mark.asyncio
    async def test_end_to_end_conversion(self, temp_storage, sample_quotes):
        """Test end-to-end conversion flow."""
        # Save sample quotes
        await temp_storage.save_quotes(sample_quotes)

        # Test conversion rate calculation
        rate_info = await temp_storage.get_conversion_rate("BTCUSDT", "ETHUSDT")
        assert rate_info is not None
        assert "rate" in rate_info

        # Expected rate: BTC price / ETH price = 45000 / 3000 = 15
        expected_rate = 45000.0 / 3000.0
        assert abs(rate_info["rate"] - expected_rate) < 0.001

        # Test amount conversion
        amount = 1.0
        converted_amount = amount * rate_info["rate"]
        assert abs(converted_amount - 15.0) < 0.001
