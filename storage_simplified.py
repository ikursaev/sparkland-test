"""
Simple storage for cryptocurrency quotes using SQLite.
"""

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import aiosqlite
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Constants
QUOTE_FRESHNESS_SECONDS = 60  # Maximum age for live conversion quotes
DEFAULT_DB_PATH = "./quotes.db"


class Quote(BaseModel):
    """Simple quote model."""

    symbol: str
    price: float
    timestamp: datetime


class QuoteStorage:
    """Simple SQLite storage for quotes."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)
        self._connection: aiosqlite.Connection | None = None

    async def initialize(self):
        """Initialize database and create tables."""
        self._connection = await aiosqlite.connect(self.db_path)
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbol_timestamp
            ON quotes(symbol, timestamp)
        """)
        await self._connection.commit()

    async def save_quotes(self, quotes: list[Quote]) -> None:
        """Save quotes to database."""
        if not quotes or not self._connection:
            return

        quote_data = [
            (quote.symbol, quote.price, quote.timestamp.isoformat()) for quote in quotes
        ]

        await self._connection.executemany(
            "INSERT INTO quotes (symbol, price, timestamp) VALUES (?, ?, ?)", quote_data
        )
        await self._connection.commit()
        logger.info(f"Saved {len(quotes)} quotes")

    async def get_latest_quote(self, symbol: str) -> Quote | None:
        """Get the latest quote for a symbol."""
        if not self._connection:
            return None

        async with self._connection.execute(
            "SELECT symbol, price, timestamp FROM quotes WHERE symbol = ? ORDER BY timestamp DESC LIMIT 1",
            (symbol,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return Quote(
                    symbol=row[0],
                    price=row[1],
                    timestamp=datetime.fromisoformat(row[2]),
                )
        return None

    async def get_conversion_rate(
        self, from_symbol: str, to_symbol: str
    ) -> dict[str, Any] | None:
        """Get conversion rate between two symbols."""
        from_quote = await self.get_latest_quote(from_symbol)
        to_quote = await self.get_latest_quote(to_symbol)

        if not from_quote or not to_quote:
            return None

        # Check if quotes are fresh (within 60 seconds)
        now = datetime.now(UTC)
        for quote in [from_quote, to_quote]:
            dt_utc = (
                quote.timestamp.replace(tzinfo=UTC)
                if quote.timestamp.tzinfo is None
                else quote.timestamp
            )
            if now - dt_utc > timedelta(seconds=QUOTE_FRESHNESS_SECONDS):
                return {"error": "quotes_outdated", "message": "Quotes are too old"}

        rate = from_quote.price / to_quote.price
        return {"rate": rate, "from_quote": from_quote, "to_quote": to_quote}

    async def cleanup_old_quotes(self, days: int = 7) -> None:
        """Remove quotes older than specified days."""
        if not self._connection:
            return

        cutoff = datetime.now(UTC) - timedelta(days=days)
        cursor = await self._connection.execute(
            "DELETE FROM quotes WHERE timestamp < ?", (cutoff.isoformat(),)
        )
        await self._connection.commit()
        if cursor.rowcount > 0:
            logger.info(f"Cleaned up {cursor.rowcount} old quotes")

    async def close(self):
        """Close database connection."""
        if self._connection:
            await self._connection.close()
