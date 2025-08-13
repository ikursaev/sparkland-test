"""
Storage data models for the crypto converter application.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class Quote(BaseModel):
    """Model representing a cryptocurrency quote."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        frozen=False,
    )

    symbol: Annotated[str, Field(description="Trading pair symbol")]
    price: Annotated[float, Field(gt=0, description="Quote price")]
    timestamp: Annotated[datetime, Field(description="Quote timestamp")]

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        """Serialize datetime to ISO format."""
        return value.isoformat()
