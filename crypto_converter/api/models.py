"""
API-specific data models for the crypto converter application.
"""

from datetime import datetime
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
)


class ConvertResponse(BaseModel):
    """Model for currency conversion response."""

    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True,
    )

    amount: Annotated[float, Field(description="Original amount")]
    from_currency: Annotated[str, Field(description="Source currency symbol")]
    to_currency: Annotated[str, Field(description="Target currency symbol")]
    converted_amount: Annotated[float, Field(description="Converted amount")]
    rate: Annotated[float, Field(gt=0, description="Conversion rate")]
    timestamp: Annotated[datetime, Field(description="Quote timestamp")]

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        """Serialize datetime to ISO format."""
        return value.isoformat()


class ErrorResponse(BaseModel):
    """Model for error responses."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    error: Annotated[str, Field(description="Error code")]
    message: Annotated[str, Field(description="Human-readable error message")]
