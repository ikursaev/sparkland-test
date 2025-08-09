"""
Data models for the crypto converter application.
"""

from datetime import datetime

from pydantic import BaseModel


class Quote(BaseModel):
    """Model representing a cryptocurrency quote."""

    symbol: str
    price: float
    timestamp: datetime

    class Config:
        """Pydantic config for Quote model."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class ConvertRequest(BaseModel):
    """Model for currency conversion request."""

    amount: float
    from_currency: str
    to_currency: str
    timestamp: datetime | None = None


class ConvertResponse(BaseModel):
    """Model for currency conversion response."""

    amount: float
    from_currency: str
    to_currency: str
    converted_amount: float
    rate: float
    timestamp: datetime

    class Config:
        """Pydantic config for ConvertResponse model."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class ErrorResponse(BaseModel):
    """Model for error responses."""

    error: str
    message: str
