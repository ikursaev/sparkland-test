"""
Storage interface for cryptocurrency quotes using async SQLite.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Final

import aiosqlite

from .models import Quote
from .settings import storage_settings

QUOTE_FRESHNESS_SECONDS: Final[int] = 60  # Maximum age for live conversion quotes

ERROR_QUOTES_OUTDATED: Final[str] = "quotes_outdated"

logger = logging.getLogger(__name__)


class QuoteStorage:
    """Async SQLite-based storage for cryptocurrency quotes."""

    def __init__(self, database_path: str | None = None):
        """Initialize the quote storage."""
        self.database_path = database_path or storage_settings.database_path
        self._connection: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Initialize the database connection and create tables."""
        await self._get_connection()
        await self._create_tables()

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get or create async database connection."""
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.database_path)
            self._connection.row_factory = aiosqlite.Row
        return self._connection

    async def _create_tables(self) -> None:
        """Create the quotes table if it doesn't exist."""
        connection = await self._get_connection()

        await connection.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

        await connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbol_timestamp
            ON quotes(symbol, timestamp)
        """)

        await connection.commit()

    async def save_quotes(self, quotes: list[Quote]) -> None:
        """Save multiple quotes to the database."""
        if not quotes:
            return

        connection = await self._get_connection()

        quote_data = [
            (quote.symbol, quote.price, quote.timestamp.isoformat()) for quote in quotes
        ]

        await connection.executemany(
            """
            INSERT INTO quotes (symbol, price, timestamp)
            VALUES (?, ?, ?)
        """,
            quote_data,
        )

        await connection.commit()
        logger.info(f"Saved {len(quotes)} quotes to database")

    async def get_quote(
        self,
        symbol: str,
        timestamp: datetime | None = None,
    ) -> Quote | None:
        """
        Get a quote for a specific symbol.

        Args:
            symbol: The currency symbol to get quote for
            timestamp: Optional timestamp. If None, gets the latest quote.
                      If provided, gets the last quote within the same day.

        Returns:
            Quote object or None if not found
        """
        if timestamp:
            return await self.get_quote_closest_timestamp(symbol, timestamp)

        connection = await self._get_connection()

        async with connection.execute(
            """
            SELECT symbol, price, timestamp
            FROM quotes
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """,
            (symbol,),
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            return Quote(
                symbol=row["symbol"],
                price=row["price"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
            )
        return None

    async def get_quote_closest_timestamp(
        self, symbol: str, target_timestamp: datetime
    ) -> Quote | None:
        """
        Get the last quote for a symbol within the same day as the target timestamp.

        This method ignores hours, minutes, and seconds, finding the latest quote
        that occurred on the same calendar day as the target timestamp.

        Args:
            symbol: The currency symbol to get quote for
            target_timestamp: Target timestamp - will find last quote on same day

        Returns:
            Quote object with the latest timestamp on that day, or None if no quotes
            found for that day
        """
        connection = await self._get_connection()

        # Get start and end of the target day (ignoring timezone for now)
        target_date = target_timestamp.date()
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = datetime.combine(target_date, datetime.max.time())

        # Handle timezone-aware timestamps
        if target_timestamp.tzinfo is not None:
            day_start = day_start.replace(tzinfo=target_timestamp.tzinfo)
            day_end = day_end.replace(tzinfo=target_timestamp.tzinfo)

        async with connection.execute(
            """
            SELECT symbol, price, timestamp
            FROM quotes
            WHERE symbol = ?
            AND timestamp >= ?
            AND timestamp <= ?
            ORDER BY timestamp DESC
            LIMIT 1
        """,
            (symbol, day_start.isoformat(), day_end.isoformat()),
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            return Quote(
                symbol=row["symbol"],
                price=row["price"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
            )
        return None

    async def get_conversion_rate(
        self, from_symbol: str, to_symbol: str, timestamp: datetime | None = None
    ) -> dict[str, Any] | None:
        """Get conversion rate between two symbols."""
        from_quote = await self.get_quote(from_symbol, timestamp)
        to_quote = await self.get_quote(to_symbol, timestamp)

        if not from_quote or not to_quote:
            return None

        if not timestamp:
            if self.is_quote_expired(from_quote) or self.is_quote_expired(to_quote):
                return {
                    "error": ERROR_QUOTES_OUTDATED,
                    "message": f"Quotes are older than {QUOTE_FRESHNESS_SECONDS} seconds",
                }

        rate = from_quote.price / to_quote.price
        return {"rate": rate, "from_quote": from_quote, "to_quote": to_quote}

    @staticmethod
    def is_quote_expired(quote: Quote) -> bool:
        """Check if a quote is too old."""
        now = datetime.now(UTC)
        max_age = timedelta(seconds=QUOTE_FRESHNESS_SECONDS)
        dt = quote.timestamp
        dt_utc = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt
        return now - dt_utc > max_age

    async def cleanup_old_quotes(self, retention_days: int = 7) -> None:
        """Remove quotes older than the retention period."""
        connection = await self._get_connection()

        cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)

        async with connection.execute(
            """
            DELETE FROM quotes
            WHERE timestamp < ?
        """,
            (cutoff_date.isoformat(),),
        ) as cursor:
            deleted_count = cursor.rowcount

        await connection.commit()

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old quotes")

    async def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
