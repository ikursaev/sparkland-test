"""
Quote consumer service that subscribes to Binance WebSocket API.
"""

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime

import websockets

from ..shared.config import Config
from ..shared.models import Quote
from ..shared.storage import QuoteStorage

logger = logging.getLogger(__name__)


class QuoteConsumer:
    """Consumer that fetches quotes from Binance WebSocket API."""

    def __init__(self):
        """Initialize the quote consumer."""
        self.storage = QuoteStorage()
        self.running = False
        self.websocket = None
        self.quotes_buffer: list[Quote] = []

    async def start(self) -> None:
        """Start the quote consumer service."""
        logger.info("Starting Quote Consumer...")

        # Initialize storage
        await self.storage.initialize()

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.running = True

        # Start background tasks
        save_task = asyncio.create_task(self._periodic_save())
        cleanup_task = asyncio.create_task(self._periodic_cleanup())
        websocket_task = asyncio.create_task(self._websocket_listener())

        try:
            # Wait for tasks to complete
            await asyncio.gather(save_task, cleanup_task, websocket_task)
        except asyncio.CancelledError:
            logger.info("Quote Consumer stopped")
        finally:
            await self.storage.close()

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    async def _websocket_listener(self) -> None:
        """Listen to Binance WebSocket for real-time quotes."""
        while self.running:
            try:
                logger.info(f"Connecting to Binance WebSocket: {Config.BINANCE_WS_URL}")
                async with websockets.connect(Config.BINANCE_WS_URL) as websocket:
                    self.websocket = websocket
                    logger.info("Connected to Binance WebSocket")

                    async for message in websocket:
                        if not self.running:
                            break

                        try:
                            data = json.loads(message)
                            quote = self._parse_binance_ticker(data)
                            if quote:
                                self.quotes_buffer.append(quote)
                                logger.debug(
                                    f"Received quote: {quote.symbol} = {quote.price}"
                                )
                        except json.JSONDecodeError:
                            logger.warning(
                                f"Failed to parse WebSocket message: {message}"
                            )
                        except Exception as e:
                            logger.error(f"Error processing WebSocket message: {e}")

            except websockets.exceptions.ConnectionClosed:
                if self.running:
                    logger.warning(
                        "WebSocket connection closed, reconnecting in 5 seconds..."
                    )
                    await asyncio.sleep(5)
            except Exception as e:
                if self.running:
                    logger.error(f"WebSocket error: {e}, reconnecting in 10 seconds...")
                    await asyncio.sleep(10)

    def _parse_binance_ticker(self, data: dict) -> Quote | None:
        """Parse Binance ticker data into Quote object."""
        try:
            # Binance ticker format: {"s": "BTCUSDT", "c": "43000.00", "E": 1234567890123}
            symbol = data.get("s", "").upper()
            price = float(data.get("c", 0))
            timestamp_ms = data.get("E", 0)

            if symbol and price > 0 and timestamp_ms > 0:
                timestamp = datetime.fromtimestamp(timestamp_ms / 1000)
                return Quote(symbol=symbol, price=price, timestamp=timestamp)

        except (ValueError, KeyError) as e:
            logger.warning(f"Failed to parse ticker data: {data}, error: {e}")

        return None

    async def _periodic_save(self) -> None:
        """Periodically save buffered quotes to storage."""
        while self.running:
            try:
                await asyncio.sleep(Config.QUOTE_SAVE_INTERVAL)

                if self.quotes_buffer:
                    quotes_to_save = self.quotes_buffer.copy()
                    self.quotes_buffer.clear()

                    await self.storage.save_quotes(quotes_to_save)
                    logger.info(f"Saved {len(quotes_to_save)} quotes to storage")

            except Exception as e:
                logger.error(f"Error during periodic save: {e}")

    async def _periodic_cleanup(self) -> None:
        """Periodically clean up old quotes from storage."""
        while self.running:
            try:
                # Clean up every hour
                await asyncio.sleep(3600)
                await self.storage.cleanup_old_quotes()

            except Exception as e:
                logger.error(f"Error during periodic cleanup: {e}")


async def main():
    """Main entry point for the quote consumer."""
    # Set up logging
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

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
