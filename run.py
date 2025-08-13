"""
Main entrypoint for the Crypto Converter application.
Usage: python run.py [api|quote-consumer]
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def setup_logging() -> None:
    """
    Set up consistent logging configuration for the application.
    Uses environment variables for configuration.
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv(
        "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    log_file = os.getenv("LOG_FILE", "crypto_converter.log")
    log_to_file = os.getenv("LOG_TO_FILE", "true").lower() == "true"

    numeric_level = getattr(logging, log_level, logging.INFO)

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_to_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path))

    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        handlers=handlers,
        force=True,  # Override any existing configuration
    )


logger = logging.getLogger(__name__)


async def main():
    if len(sys.argv) != 2:
        print("Usage: python run.py [api|quote-consumer]")
        print("  api            - Start the Currency Conversion API")
        print("  quote-consumer - Start the Quote Consumer")
        sys.exit(1)

    command = sys.argv[1].lower()

    setup_logging()

    if command == "api":
        from crypto_converter.api.service import main as run_service

        logger.info("Starting API service...")
    elif command == "quote-consumer":
        from crypto_converter.quote_consumer.service import main as run_service

        logger.info("Starting Quote Consumer...")
    else:
        print(f"Unknown command: {command}")
        print("Usage: python run.py [api|quote-consumer]")
        print("  api            - Start the Currency Conversion API")
        print("  quote-consumer - Start the Quote Consumer")
        sys.exit(1)
    await run_service()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"Application failed: {e}")
        sys.exit(1)
