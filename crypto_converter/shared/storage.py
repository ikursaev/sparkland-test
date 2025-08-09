"""
Storage interface for cryptocurrency quotes using SQLite.
"""

import logging
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

from .config import Config
from .models import Quote

logger = logging.getLogger(__name__)


class QuoteStorage:
    """SQLite-based storage for cryptocurrency quotes."""

    def __init__(self, database_path: str | None = None):
        """Initialize the quote storage."""
        self.database_path = database_path or Config.DATABASE_PATH
        self._connection: sqlite3.Connection | None = None

    async def initialize(self) -> None:
        """Initialize the database connection and create tables."""
        await self._get_connection()
        await self._create_tables()

    async def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.database_path, check_same_thread=False
            )
            self._connection.row_factory = sqlite3.Row
        return self._connection

    async def _create_tables(self) -> None:
        """Create the quotes table if it doesn't exist."""
        connection = await self._get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbol_timestamp
            ON quotes(symbol, timestamp)
        """)

        connection.commit()

    async def save_quotes(self, quotes: list[Quote]) -> None:
        """Save multiple quotes to the database."""
        if not quotes:
            return

        connection = await self._get_connection()
        cursor = connection.cursor()

        quote_data = [
            (
                quote.symbol,
                quote.price,
                quote.timestamp.isoformat(),
            )
            for quote in quotes
        ]

        cursor.executemany(
            """
            INSERT INTO quotes (symbol, price, timestamp)
            VALUES (?, ?, ?)
        """,
            quote_data,
        )

        connection.commit()
        logger.info(f"Saved {len(quotes)} quotes to database")

    async def get_quote(
        self, symbol: str, timestamp: datetime | None = None
    ) -> Quote | None:
        """
        Get a quote for a specific symbol.

        Args:
            symbol: The currency symbol to get quote for
            timestamp: Optional timestamp. If None, gets the latest quote.
                      If provided, gets the quote with exact timestamp match.

        Returns:
            Quote object or None if not found (exact timestamp match required)
        """
        connection = await self._get_connection()
        cursor = connection.cursor()

        if timestamp is None:
            # Get the latest quote
            cursor.execute(
                """
                SELECT symbol, price, timestamp
                FROM quotes
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """,
                (symbol,),
            )
        else:
            # Get quote with exact timestamp match
            cursor.execute(
                """
                SELECT symbol, price, timestamp
                FROM quotes
                WHERE symbol = ? AND timestamp = ?
                LIMIT 1
            """,
                (symbol, timestamp.isoformat()),
            )

        row = cursor.fetchone()
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

        # Check if quotes are recent enough (less than 1 minute old) for real-time requests
        if not timestamp:
            now = datetime.now(UTC)
            # Convert naive timestamps to UTC for comparison
            from_timestamp = (
                from_quote.timestamp.replace(tzinfo=UTC)
                if from_quote.timestamp.tzinfo is None
                else from_quote.timestamp
            )
            to_timestamp = (
                to_quote.timestamp.replace(tzinfo=UTC)
                if to_quote.timestamp.tzinfo is None
                else to_quote.timestamp
            )

            if (now - from_timestamp).total_seconds() > 60 or (
                now - to_timestamp
            ).total_seconds() > 60:
                return {
                    "error": "quotes_outdated",
                    "message": "Quotes are older than 1 minute",
                }

        rate = from_quote.price / to_quote.price
        return {"rate": rate, "from_quote": from_quote, "to_quote": to_quote}

    async def cleanup_old_quotes(self) -> None:
        """Remove quotes older than the retention period."""
        connection = await self._get_connection()
        cursor = connection.cursor()

        cutoff_date = datetime.now(UTC) - timedelta(days=Config.QUOTE_RETENTION_DAYS)

        cursor.execute(
            """
            DELETE FROM quotes
            WHERE timestamp < ?
        """,
            (cutoff_date.isoformat(),),
        )

        deleted_count = cursor.rowcount
        connection.commit()

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old quotes")

    async def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
