"""
Quote consumer settings using Pydantic for environment-based configuration.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class QuoteConsumerSettings(BaseSettings):
    """Quote consumer service configuration using Pydantic settings."""

    binance_rest_url: str = Field(
        default="https://api.binance.com",
        description="Binance REST API base URL",
    )

    http_polling_interval: int = Field(
        default=10,
        description="Interval in seconds to poll REST API for quotes",
    )

    quote_save_interval: int = Field(
        default=30, description="Interval in seconds to save quotes to storage"
    )

    quote_retention_days: int = Field(
        default=7, description="Number of days to retain quotes in storage"
    )

    log_level: str = Field(default="INFO", description="Logging level")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Create a global instance
quote_consumer_settings = QuoteConsumerSettings()
