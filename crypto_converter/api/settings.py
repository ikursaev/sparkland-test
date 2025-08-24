"""
API settings using Pydantic for environment-based configuration.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    """API service configuration using Pydantic settings."""

    api_host: str = Field(default="0.0.0.0", description="API host address")
    api_port: int = Field(default=8000, description="API port number")
    log_level: str = Field(default="INFO", description="Logging level")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


api_settings = APISettings()
