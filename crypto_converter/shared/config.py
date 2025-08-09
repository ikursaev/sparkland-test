"""
Shared configuration module for the crypto converter application.
"""

import os


class Config:
    """Configuration class for environment variables."""

    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "./quotes.db")

    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # Quote Consumer Configuration
    BINANCE_WS_URL: str = os.getenv(
        "BINANCE_WS_URL",
        "wss://stream.binance.com:9443/ws/btcusdt@ticker/ethusdt@ticker/adausdt@ticker/bnbusdt@ticker",
    )
    QUOTE_SAVE_INTERVAL: int = int(os.getenv("QUOTE_SAVE_INTERVAL", "30"))
    QUOTE_RETENTION_DAYS: int = int(os.getenv("QUOTE_RETENTION_DAYS", "7"))

    # General Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
