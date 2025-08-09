"""
Main entrypoint for the Crypto Converter application.
Usage: python run.py [api|quote-consumer]
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from crypto_converter.shared.config import Config


async def run_api():
    """Run the Currency Conversion API."""
    try:
        from crypto_converter.api.service import main as api_main

        await api_main()
    except ImportError as e:
        logging.error(f"Failed to import API service: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"API service failed: {e}")
        sys.exit(1)


async def run_quote_consumer():
    """Run the Quote Consumer service."""
    try:
        from crypto_converter.quote_consumer.service import main as consumer_main

        await consumer_main()
    except ImportError as e:
        logging.error(f"Failed to import Quote Consumer service: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Quote Consumer service failed: {e}")
        sys.exit(1)


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("crypto_converter.log"),
        ],
    )


def print_usage():
    """Print usage information."""
    print("""
Crypto Converter - Cryptocurrency conversion API and quote consumer

Usage: python run.py [COMMAND]

Commands:
    api             Start the Currency Conversion API server
    quote-consumer  Start the Quote Consumer service
    help            Show this help message

Examples:
    python run.py api
    python run.py quote-consumer

Environment Variables:
    See .env.example for configuration options
    """)


async def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()

    # Set up logging
    setup_logging()
    logger = logging.getLogger(__name__)

    if command == "api":
        logger.info("Starting Currency Conversion API...")
        await run_api()
    elif command == "quote-consumer":
        logger.info("Starting Quote Consumer...")
        await run_quote_consumer()
    elif command in ["help", "-h", "--help"]:
        print_usage()
    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"Application failed: {e}")
        sys.exit(1)
