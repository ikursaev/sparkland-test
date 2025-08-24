"""
Storage settings using Pydantic for environment-based configuration.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageSettings(BaseSettings):
    """Storage configuration for database and storage-related settings."""

    # Database Configuration
    database_path: str = Field(
        default="./quotes.db", description="Path to SQLite database file"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Create a global instance
storage_settings = StorageSettings()
