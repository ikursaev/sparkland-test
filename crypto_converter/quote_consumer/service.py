"""
Quote consumer service that fetches quotes from Binance REST API.
"""

import asyncio
import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Final

import aiohttp

from ..storage.models import Quote
from ..storage.quote_storage import QuoteStorage
from .settings import quote_consumer_settings

CLEANUP_INTERVAL: Final[int] = 3600  # seconds (1 hour)

logger = logging.getLogger(__name__)


class QuoteConsumer:
    """Consumer that fetches quotes from Binance REST API."""

    def __init__(self) -> None:
        """Initialize the quote consumer."""
        self.storage = QuoteStorage()
        self.quotes_buffer: list[Quote] = []
        self._symbols: list[str] = []

    async def _fetch_trading_symbols(self) -> list[str]:
        """Fetch all trading symbols from Binance exchangeInfo API."""
        if self._symbols:
            return self._symbols

        url = f"{quote_consumer_settings.binance_rest_url}/api/v3/exchangeInfo"

        async with (
            aiohttp.ClientSession() as session,
            session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response,
        ):
            response.raise_for_status()
            data = await response.json()

            self._symbols = [
                symbol["symbol"]
                for symbol in data["symbols"]
                if symbol["status"] == "TRADING"
            ]

            logger.info(f"Fetched {len(self._symbols)} trading symbols from Binance")
            return self._symbols

    async def _fetch_quotes_http(self) -> list[Quote]:
        """Fetch all quotes using Binance REST API."""
        url = f"{quote_consumer_settings.binance_rest_url}/api/v3/ticker/price"

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response,
            ):
                response.raise_for_status()
                data = await response.json()
                current_time = datetime.now(UTC)

                quotes = [
                    quote
                    for item in data
                    if (quote := self._parse_binance_rest_ticker(item, current_time))
                ]

                logger.debug(f"Fetched {len(quotes)} quotes via HTTP")
                return quotes

        except Exception as e:
            logger.error(f"Error fetching quotes via HTTP: {e}")
            return []

    def _parse_binance_rest_ticker(
        self, data: dict, timestamp: datetime
    ) -> Quote | None:
        """Parse Binance REST API ticker data into Quote object."""
        try:
            if "symbol" not in data or "price" not in data:
                return None

            symbol = data["symbol"].upper()
            price = float(data["price"])

            if symbol and price > 0:
                return Quote(symbol=symbol, price=price, timestamp=timestamp)

        except (ValueError, KeyError) as e:
            logger.warning(f"Failed to parse REST ticker data: {data}, error: {e}")

    @asynccontextmanager
    async def _managed_lifecycle(self) -> AsyncGenerator[None, None]:
        """Async context manager for proper resource management."""
        try:
            await self.storage.initialize()
            yield
        finally:
            await self.storage.close()

    async def start(self) -> None:
        """Start the quote consumer service using modern structured concurrency."""
        logger.info("Starting Quote Consumer in HTTP mode...")

        async with self._managed_lifecycle():
            try:
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self._http_handler())
                    tg.create_task(self._periodic_save())
                    tg.create_task(self._periodic_cleanup())
            except* Exception as eg:
                for exc in eg.exceptions:
                    logger.error(f"Service error: {exc}")
                raise

    async def _http_handler(self) -> None:
        """Handle HTTP polling for quotes."""
        try:
            while True:
                try:
                    quotes = await self._fetch_quotes_http()
                    if quotes:
                        self.quotes_buffer.extend(quotes)
                        logger.debug(f"Added {len(quotes)} quotes to buffer via HTTP")
                    await asyncio.sleep(quote_consumer_settings.http_polling_interval)
                except Exception as e:
                    logger.error(f"HTTP handler error: {e}, retrying...")
                    await asyncio.sleep(quote_consumer_settings.http_polling_interval)
        except asyncio.CancelledError:
            logger.info("HTTP handler cancelled")
            raise

    async def _periodic_save(self) -> None:
        """Periodically save buffered quotes to storage with batching."""
        try:
            while True:
                await asyncio.sleep(quote_consumer_settings.quote_save_interval)
                await self._flush_quotes_buffer()
        except asyncio.CancelledError:
            logger.info("Periodic save task cancelled")
            # Perform final flush before shutdown
            await self._flush_quotes_buffer()
            raise
        except Exception as e:
            logger.error(f"Error during periodic save: {e}")
            raise

    async def _flush_quotes_buffer(self) -> None:
        """Flush quotes buffer to storage."""
        if not (quotes_to_save := self.quotes_buffer.copy()):
            return

        self.quotes_buffer.clear()
        await self.storage.save_quotes(quotes_to_save)
        logger.info(f"Saved {len(quotes_to_save)} quotes to storage")

    async def _periodic_cleanup(self) -> None:
        """Periodically clean up old quotes from storage."""
        try:
            while True:
                await asyncio.sleep(CLEANUP_INTERVAL)
                await self.storage.cleanup_old_quotes(
                    quote_consumer_settings.quote_retention_days
                )
                logger.info("Completed periodic cleanup")
        except asyncio.CancelledError:
            logger.info("Periodic cleanup task cancelled")
            raise
        except Exception as e:
            logger.error(f"Error during periodic cleanup: {e}")
            raise


async def main() -> None:
    """Main entry point for the quote consumer."""
    consumer = QuoteConsumer()
    await consumer.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Quote Consumer stopped by user")
    except Exception as e:
        logger.error(f"Quote Consumer failed: {e}")
        sys.exit(1)
