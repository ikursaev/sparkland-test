"""FastAPI application for cryptocurrency conversion."""

import logging
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Annotated, Final

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BeforeValidator

from ..storage.quote_storage import QuoteStorage
from .models import ConvertResponse, ErrorResponse
from .settings import api_settings
from .validators import validate_same_base_currencies, validate_timestamp

MAX_CONVERSION_AMOUNT: Final[float] = 1_000_000_000
MIN_CURRENCY_SYMBOL_LENGTH: Final[int] = 6
MAX_CURRENCY_SYMBOL_LENGTH: Final[int] = 12

ERROR_QUOTES_NOT_FOUND: Final[str] = "quotes_not_found"
ERROR_INTERNAL_ERROR: Final[str] = "internal_error"
ERROR_NOT_FOUND: Final[str] = "not_found"

logger = logging.getLogger(__name__)


async def get_quote_storage() -> AsyncGenerator[QuoteStorage, None]:
    """
    Dependency function to provide storage instance.

    Returns:
        QuoteStorage: Initialized storage instance
    """
    storage = QuoteStorage()
    try:
        await storage.initialize()
        yield storage
    finally:
        await storage.close()


CurrencyType = Annotated[
    str,
    BeforeValidator(str.upper),
    Query(
        min_length=MIN_CURRENCY_SYMBOL_LENGTH,
        max_length=MAX_CURRENCY_SYMBOL_LENGTH,
        pattern=r"^[A-Za-z0-9]+$",
        description="Currency symbol",
        examples=["BTCUSDT", "ETHUSDT", "ADAUSDT"],
    ),
]


app = FastAPI(
    title="Crypto Converter API",
    description="API to convert amounts of crypto currencies using real-time quotes",
    version="1.0.0",
)


@app.get("/", response_model=dict[str, str])
async def root() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        dict[str, str]: Health status information
    """
    return {"message": "Crypto Converter API is running", "status": "healthy"}


@app.get("/convert", response_model=ConvertResponse)
async def convert_currency(
    storage: Annotated[QuoteStorage, Depends(get_quote_storage)],
    amount: Annotated[
        float, Query(gt=0, le=MAX_CONVERSION_AMOUNT, description="Amount to convert")
    ],
    from_currency: Annotated[CurrencyType, Query(alias="from")],
    to_currency: Annotated[CurrencyType, Query(alias="to")],
    timestamp: Annotated[
        datetime | None,
        BeforeValidator(validate_timestamp),
        Query(description="Optional timestamp for historical conversion"),
    ] = None,
) -> ConvertResponse:
    """
    Convert cryptocurrency amounts between different currencies.

    This endpoint performs real-time or historical cryptocurrency conversions
    between supported trading pairs. The conversion rates are sourced from
    live market data and stored quotes.

    Args:
        storage: Storage dependency for quote access
        amount: Amount to convert
        from_currency: Source currency symbol
        to_currency: Target currency symbol
        timestamp: Optional timestamp for historical conversion

    Returns:
        ConvertResponse: Converted amount and rate information

    Raises:
        HTTPException: For various error conditions including:
            - 400: Invalid parameters or unsupported conversion
            - 404: No quotes available for the requested pair
            - 500: Internal server errors
    """
    try:
        validate_same_base_currencies(from_currency, to_currency)

        rate_info = await storage.get_conversion_rate(
            from_currency,
            to_currency,
            timestamp,
        )

        match rate_info:
            case None:
                raise HTTPException(
                    status_code=404,
                    detail=ErrorResponse(
                        error=ERROR_QUOTES_NOT_FOUND,
                        message=f"No quotes available for conversion from {from_currency} to {to_currency}",
                    ).model_dump(),
                )
            case {"error": error_code, "message": error_message}:
                raise HTTPException(
                    status_code=400,
                    detail=ErrorResponse(
                        error=error_code, message=error_message
                    ).model_dump(),
                )
            case {"rate": rate, "from_quote": from_quote}:
                converted_amount = amount * rate
                return ConvertResponse(
                    amount=amount,
                    from_currency=from_currency,
                    to_currency=to_currency,
                    converted_amount=converted_amount,
                    rate=rate,
                    timestamp=from_quote.timestamp,
                )
            case _:
                # This should not happen with proper storage implementation
                raise HTTPException(
                    status_code=500,
                    detail=ErrorResponse(
                        error=ERROR_INTERNAL_ERROR,
                        message="Invalid rate info structure returned from storage",
                    ).model_dump(),
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in conversion: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error=ERROR_INTERNAL_ERROR,
                message="An unexpected error occurred during conversion",
            ).model_dump(),
        ) from e


@app.exception_handler(404)
async def not_found_handler(_: Request, __: Exception) -> JSONResponse:
    """Handle 404 errors.

    Returns:
        JSONResponse: Error response in JSON format
    """
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            error=ERROR_NOT_FOUND, message="Endpoint not found"
        ).model_dump(),
    )


@app.exception_handler(500)
async def internal_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Handle internal server errors.

    Args:
        exc: The exception that was raised

    Returns:
        JSONResponse: Error response in JSON format
    """
    logger.error(f"Internal server error: {exc}", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=ERROR_INTERNAL_ERROR, message="An internal server error occurred"
        ).model_dump(),
    )


async def main() -> None:
    """Main entry point for the API server."""
    config = uvicorn.Config(
        app,
        host=api_settings.api_host,
        port=api_settings.api_port,
        log_level=api_settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
