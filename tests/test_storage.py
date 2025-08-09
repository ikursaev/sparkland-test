"""
Tests for the storage functionality.
"""

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

# Add project root to path before importing our modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import our modules after path setup
from crypto_converter.shared.models import Quote  # noqa: E402


class TestQuoteStorage:
    """Test cases for QuoteStorage class."""

    @pytest.mark.asyncio
    async def test_save_and_retrieve_quotes(self, temp_storage, sample_quotes):
        """Test saving and retrieving quotes."""
        # Save quotes
        await temp_storage.save_quotes(sample_quotes)

        # Retrieve latest quote
        btc_quote = await temp_storage.get_quote("BTCUSDT")
        assert btc_quote is not None
        assert btc_quote.symbol == "BTCUSDT"
        assert btc_quote.price == 45000.0

    @pytest.mark.asyncio
    async def test_get_conversion_rate(self, temp_storage, sample_quotes):
        """Test getting conversion rate between currencies."""
        # Save quotes
        await temp_storage.save_quotes(sample_quotes)

        # Get conversion rate
        rate_info = await temp_storage.get_conversion_rate("BTCUSDT", "ETHUSDT")
        assert rate_info is not None
        assert "rate" in rate_info
        assert rate_info["rate"] == 45000.0 / 3000.0  # BTC/ETH rate

    @pytest.mark.asyncio
    async def test_quotes_outdated_error(self, temp_storage):
        """Test that outdated quotes return an error."""
        # Create old quotes
        old_time = datetime.now(UTC) - timedelta(minutes=2)
        old_quotes = [
            Quote(symbol="BTCUSDT", price=45000.0, timestamp=old_time),
            Quote(symbol="ETHUSDT", price=3000.0, timestamp=old_time),
        ]

        await temp_storage.save_quotes(old_quotes)

        # Try to get conversion rate
        rate_info = await temp_storage.get_conversion_rate("BTCUSDT", "ETHUSDT")
        assert rate_info is not None
        assert "error" in rate_info
        assert rate_info["error"] == "quotes_outdated"

    @pytest.mark.asyncio
    async def test_cleanup_old_quotes(self, temp_storage):
        """Test cleanup of old quotes."""
        # Create old and new quotes
        old_time = datetime.now(UTC) - timedelta(days=8)
        new_time = datetime.now(UTC)

        old_quotes = [Quote(symbol="BTCUSDT", price=45000.0, timestamp=old_time)]
        new_quotes = [Quote(symbol="ETHUSDT", price=3000.0, timestamp=new_time)]

        await temp_storage.save_quotes(old_quotes + new_quotes)

        # Clean up old quotes
        await temp_storage.cleanup_old_quotes()

        # Verify old quote is gone, new quote remains
        btc_quote = await temp_storage.get_quote("BTCUSDT")
        eth_quote = await temp_storage.get_quote("ETHUSDT")

        assert btc_quote is None  # Old quote should be deleted
        assert eth_quote is not None  # New quote should remain

    @pytest.mark.asyncio
    async def test_get_quote_at_time(self, temp_storage):
        """Test retrieving quotes at specific timestamps."""
        # Create quotes with different timestamps
        base_time = datetime.now(UTC) - timedelta(hours=1)
        quotes = [
            Quote(symbol="BTCUSDT", price=44000.0, timestamp=base_time),
            Quote(
                symbol="BTCUSDT",
                price=45000.0,
                timestamp=base_time + timedelta(minutes=30),
            ),
            Quote(
                symbol="BTCUSDT",
                price=46000.0,
                timestamp=base_time + timedelta(hours=1),
            ),
        ]

        await temp_storage.save_quotes(quotes)

        # Test 1: Get quote at exact timestamp (should find it)
        quote = await temp_storage.get_quote("BTCUSDT", base_time)
        assert quote is not None
        assert quote.price == 44000.0  # Should get the first quote (exact match)

        # Test 2: Get quote at non-existent timestamp (should return None)
        target_time = base_time + timedelta(minutes=15)
        quote = await temp_storage.get_quote("BTCUSDT", target_time)
        assert quote is None  # No exact match, should return None

        # Test 3: Get quote at another exact timestamp
        exact_time = base_time + timedelta(minutes=30)
        quote = await temp_storage.get_quote("BTCUSDT", exact_time)
        assert quote is not None
        assert quote.price == 45000.0  # Should get the second quote (exact match)
