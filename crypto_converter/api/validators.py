"""
Custom validators for API parameters.
"""

from datetime import datetime
from typing import Final

from fastapi import HTTPException

from .models import ErrorResponse

ERROR_UNSUPPORTED_CONVERSION: Final[str] = "unsupported_conversion"


def validate_same_base_currencies(from_currency: str, to_currency: str) -> None:
    """
    Validate that both currencies share the same base currency.

    This function checks if the conversion is a direct pair (not cross-currency).
    Both currencies must share a common base currency for the conversion to be supported.

    Args:
        from_currency: Source currency symbol (e.g., 'BTCUSDT')
        to_currency: Target currency symbol (e.g., 'ETHUSDT')

    Raises:
        HTTPException: If the currencies don't share the same base currency
    """
    # Try to find a common suffix (base currency) between both symbols
    # Check from the longest possible base currency down to 3 characters
    min_length = min(len(from_currency), len(to_currency))
    for base_length in range(min_length - 2, 2, -1):
        suffix = from_currency[-base_length:]
        if to_currency.endswith(suffix):
            return

    raise HTTPException(
        status_code=422,
        detail=ErrorResponse(
            error=ERROR_UNSUPPORTED_CONVERSION,
            message=f"Cross-currency conversion from {from_currency} to {to_currency} is not supported. "
            f"Both currencies must share the same base currency.",
        ).model_dump(),
    )


def validate_timestamp(v: str | datetime | None) -> datetime | None:
    """Validate and convert timestamp from string to datetime."""
    if v is None or v == "":
        return None

    if isinstance(v, datetime):
        return v

    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValueError(
            "Timestamp must be in ISO format (e.g., '2023-01-01T12:00:00Z')"
        ) from e
