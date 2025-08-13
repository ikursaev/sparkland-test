"""
Tests for the storage functionality.
"""

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crypto_converter.storage.models import Quote  # noqa: E402


class TestQuoteStorage:
    """Test cases for QuoteStorage class."""

    @pytest.mark.asyncio
    async def test_save_and_retrieve_quotes(self, temp_storage, sample_quotes):
        """Test saving and retrieving quotes."""
        await temp_storage.save_quotes(sample_quotes)

        btc_quote = await temp_storage.get_quote("BTCUSDT")
        assert btc_quote is not None
        assert btc_quote.symbol == "BTCUSDT"
        assert btc_quote.price == 45000.0

    @pytest.mark.asyncio
    async def test_get_conversion_rate(self, temp_storage, sample_quotes):
        """Test getting conversion rate between currencies."""
        await temp_storage.save_quotes(sample_quotes)

        rate_info = await temp_storage.get_conversion_rate("BTCUSDT", "ETHUSDT")
        assert rate_info is not None
        assert "rate" in rate_info
        assert rate_info["rate"] == 45000.0 / 3000.0

    @pytest.mark.asyncio
    async def test_quotes_outdated_error(self, temp_storage):
        """Test that outdated quotes return an error."""
        old_time = datetime.now(UTC) - timedelta(minutes=2)
        old_quotes = [
            Quote(symbol="BTCUSDT", price=45000.0, timestamp=old_time),
            Quote(symbol="ETHUSDT", price=3000.0, timestamp=old_time),
        ]

        await temp_storage.save_quotes(old_quotes)

        rate_info = await temp_storage.get_conversion_rate("BTCUSDT", "ETHUSDT")
        assert rate_info is not None
        assert "error" in rate_info
        assert rate_info["error"] == "quotes_outdated"

    @pytest.mark.asyncio
    async def test_cleanup_old_quotes(self, temp_storage):
        """Test cleanup of old quotes."""
        old_time = datetime.now(UTC) - timedelta(days=8)
        new_time = datetime.now(UTC)

        old_quotes = [Quote(symbol="BTCUSDT", price=45000.0, timestamp=old_time)]
        new_quotes = [Quote(symbol="ETHUSDT", price=3000.0, timestamp=new_time)]

        await temp_storage.save_quotes(old_quotes + new_quotes)

        await temp_storage.cleanup_old_quotes()

        btc_quote = await temp_storage.get_quote("BTCUSDT")
        eth_quote = await temp_storage.get_quote("ETHUSDT")

        assert btc_quote is None
        assert eth_quote is not None

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

        # Test 1: Get quote with timestamp (should get the last quote of that day)
        quote = await temp_storage.get_quote("BTCUSDT", base_time)
        assert quote is not None
        assert quote.price == 46000.0  # Should get the last quote of the day

        # Test 2: Get quote at a time between quotes (should get the last quote of that day)
        target_time = base_time + timedelta(minutes=15)
        quote = await temp_storage.get_quote("BTCUSDT", target_time)
        assert quote is not None
        assert quote.price == 46000.0  # Should get the last quote of the day

        # Test 3: Get quote at another timestamp (should still get the last quote of that day)
        exact_time = base_time + timedelta(minutes=30)
        quote = await temp_storage.get_quote("BTCUSDT", exact_time)
        assert quote is not None
        assert quote.price == 46000.0  # Should get the last quote of the day

    @pytest.mark.asyncio
    async def test_get_quote_closest_timestamp_same_day(self, temp_storage):
        """Test closest timestamp lookup within the same day."""
        # Create quotes throughout a single day
        base_date = datetime(2025, 1, 15, tzinfo=UTC)
        quotes = [
            Quote(
                symbol="BTCUSDT",
                price=44000.0,
                timestamp=base_date.replace(hour=8, minute=30),
            ),
            Quote(
                symbol="BTCUSDT",
                price=45000.0,
                timestamp=base_date.replace(hour=12, minute=0),
            ),
            Quote(
                symbol="BTCUSDT",
                price=46000.0,
                timestamp=base_date.replace(hour=18, minute=45),
            ),
            Quote(
                symbol="BTCUSDT",
                price=47000.0,
                timestamp=base_date.replace(hour=23, minute=59),
            ),
        ]

        await temp_storage.save_quotes(quotes)

        # Test 1: Request timestamp in the morning should get last quote of that day
        morning_time = base_date.replace(hour=9, minute=15)
        quote = await temp_storage.get_quote_closest_timestamp("BTCUSDT", morning_time)
        assert quote is not None
        assert quote.price == 47000.0  # Should get the last quote of the day
        assert quote.timestamp.date() == morning_time.date()

        # Test 2: Request timestamp in the evening should still get last quote of that day
        evening_time = base_date.replace(hour=20, minute=30)
        quote = await temp_storage.get_quote_closest_timestamp("BTCUSDT", evening_time)
        assert quote is not None
        assert quote.price == 47000.0  # Should get the last quote of the day

        # Test 3: Request timestamp after last quote should still get last quote of that day
        late_time = base_date.replace(hour=23, minute=58)
        quote = await temp_storage.get_quote_closest_timestamp("BTCUSDT", late_time)
        assert quote is not None
        assert quote.price == 47000.0  # Should get the last quote of the day

    @pytest.mark.asyncio
    async def test_get_quote_closest_timestamp_no_quotes_on_day(self, temp_storage):
        """Test closest timestamp lookup when no quotes exist for the target day."""
        # Create quotes for day 1 and day 3, but not day 2
        base_date = datetime(2025, 1, 15, tzinfo=UTC)
        quotes = [
            Quote(symbol="BTCUSDT", price=44000.0, timestamp=base_date),
            Quote(
                symbol="BTCUSDT", price=46000.0, timestamp=base_date + timedelta(days=2)
            ),
        ]

        await temp_storage.save_quotes(quotes)

        # Request quote for day 2 (no quotes available)
        target_time = base_date + timedelta(days=1, hours=12)
        quote = await temp_storage.get_quote_closest_timestamp("BTCUSDT", target_time)
        assert quote is None

    @pytest.mark.asyncio
    async def test_get_quote_closest_timestamp_multiple_symbols(self, temp_storage):
        """Test closest timestamp lookup with multiple symbols."""
        base_date = datetime(2025, 1, 15, tzinfo=UTC)
        quotes = [
            Quote(
                symbol="BTCUSDT", price=44000.0, timestamp=base_date.replace(hour=10)
            ),
            Quote(
                symbol="BTCUSDT", price=45000.0, timestamp=base_date.replace(hour=20)
            ),
            Quote(symbol="ETHUSDT", price=3000.0, timestamp=base_date.replace(hour=9)),
            Quote(symbol="ETHUSDT", price=3100.0, timestamp=base_date.replace(hour=15)),
        ]

        await temp_storage.save_quotes(quotes)

        target_time = base_date.replace(hour=12)

        # Test BTC - should get last quote (20:00)
        btc_quote = await temp_storage.get_quote_closest_timestamp(
            "BTCUSDT", target_time
        )
        assert btc_quote is not None
        assert btc_quote.price == 45000.0

        # Test ETH - should get last quote (15:00)
        eth_quote = await temp_storage.get_quote_closest_timestamp(
            "ETHUSDT", target_time
        )
        assert eth_quote is not None
        assert eth_quote.price == 3100.0

        # Test non-existent symbol
        ada_quote = await temp_storage.get_quote_closest_timestamp(
            "ADAUSDT", target_time
        )
        assert ada_quote is None

    @pytest.mark.asyncio
    async def test_get_quote_closest_timestamp_timezone_aware(self, temp_storage):
        """Test closest timestamp lookup with timezone-aware timestamps."""
        from datetime import timezone

        # Create timezone-aware timestamps
        est_tz = timezone(timedelta(hours=-5))  # EST timezone
        base_date = datetime(2025, 1, 15, 10, 0, tzinfo=est_tz)

        quotes = [
            Quote(symbol="BTCUSDT", price=44000.0, timestamp=base_date),
            Quote(
                symbol="BTCUSDT", price=45000.0, timestamp=base_date.replace(hour=15)
            ),
            Quote(
                symbol="BTCUSDT", price=46000.0, timestamp=base_date.replace(hour=20)
            ),
        ]

        await temp_storage.save_quotes(quotes)

        # Request with same timezone
        target_time = base_date.replace(hour=12)
        quote = await temp_storage.get_quote_closest_timestamp("BTCUSDT", target_time)
        assert quote is not None
        assert quote.price == 46000.0  # Should get the last quote of the day

    @pytest.mark.asyncio
    async def test_get_quote_closest_timestamp_naive_timestamps(self, temp_storage):
        """Test closest timestamp lookup with naive (non-timezone-aware) timestamps."""
        # Create naive timestamps (no timezone info)
        base_date = datetime(2025, 1, 15, 10, 0)  # No tzinfo

        quotes = [
            Quote(symbol="BTCUSDT", price=44000.0, timestamp=base_date),
            Quote(
                symbol="BTCUSDT", price=45000.0, timestamp=base_date.replace(hour=15)
            ),
            Quote(
                symbol="BTCUSDT", price=46000.0, timestamp=base_date.replace(hour=20)
            ),
        ]

        await temp_storage.save_quotes(quotes)

        # Request with naive timestamp
        target_time = base_date.replace(hour=12)
        quote = await temp_storage.get_quote_closest_timestamp("BTCUSDT", target_time)
        assert quote is not None
        assert quote.price == 46000.0  # Should get the last quote of the day

    @pytest.mark.asyncio
    async def test_get_quote_closest_timestamp_edge_of_day(self, temp_storage):
        """Test closest timestamp lookup at the very beginning and end of day."""
        base_date = datetime(2025, 1, 15, tzinfo=UTC)
        quotes = [
            Quote(
                symbol="BTCUSDT",
                price=44000.0,
                timestamp=base_date.replace(hour=0, minute=0, second=1),
            ),
            Quote(
                symbol="BTCUSDT",
                price=45000.0,
                timestamp=base_date.replace(hour=12, minute=30),
            ),
            Quote(
                symbol="BTCUSDT",
                price=46000.0,
                timestamp=base_date.replace(hour=23, minute=59, second=59),
            ),
        ]

        await temp_storage.save_quotes(quotes)

        # Test at very beginning of day
        start_of_day = base_date.replace(hour=0, minute=0, second=0)
        quote = await temp_storage.get_quote_closest_timestamp("BTCUSDT", start_of_day)
        assert quote is not None
        assert quote.price == 46000.0  # Should get the last quote of the day

        # Test at very end of day
        end_of_day = base_date.replace(hour=23, minute=59, second=59)
        quote = await temp_storage.get_quote_closest_timestamp("BTCUSDT", end_of_day)
        assert quote is not None
        assert quote.price == 46000.0  # Should get the last quote of the day

    @pytest.mark.asyncio
    async def test_get_quote_last_within_day(self, temp_storage):
        """Test that get_quote with timestamp returns last quote of the day."""
        base_date = datetime(2025, 1, 15, tzinfo=UTC)
        quotes = [
            Quote(
                symbol="BTCUSDT", price=44000.0, timestamp=base_date.replace(hour=10)
            ),
            Quote(
                symbol="BTCUSDT", price=45000.0, timestamp=base_date.replace(hour=15)
            ),
        ]

        await temp_storage.save_quotes(quotes)

        target_time = base_date.replace(hour=12)

        # Test the behavior - should always get the last quote of the day
        quote = await temp_storage.get_quote("BTCUSDT", target_time)
        assert quote is not None
        assert quote.price == 45000.0  # Should get the last quote of the day

        # Test with different times within the same day - should always get the same last quote
        early_time = base_date.replace(hour=8)  # Before any quotes
        quote_early = await temp_storage.get_quote("BTCUSDT", early_time)
        assert quote_early is not None
        assert (
            quote_early.price == 45000.0
        )  # Should still get the last quote of the day
