"""
FastAPI application for cryptocurrency conversion.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from ..shared.config import Config
from ..shared.models import ConvertResponse, ErrorResponse
from ..shared.storage import QuoteStorage

logger = logging.getLogger(__name__)

# Global storage instance
storage: QuoteStorage | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    global storage
    storage = QuoteStorage()
    await storage.initialize()
    logger.info("Currency Conversion API started")

    yield

    # Shutdown
    if storage:
        await storage.close()
    logger.info("Currency Conversion API stopped")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Crypto Converter API",
    description="API to convert amounts of crypto currencies using real-time quotes",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/", response_model=dict)
async def root():
    """Health check endpoint."""
    return {"message": "Crypto Converter API is running", "status": "healthy"}


@app.get("/convert", response_model=ConvertResponse)
async def convert_currency(
    amount: float = Query(..., description="Amount to convert", gt=0),
    from_currency: str = Query(..., description="Source currency symbol", alias="from"),
    to_currency: str = Query(..., description="Target currency symbol", alias="to"),
    timestamp: str | None = Query(
        None, description="Optional timestamp (ISO format) for historical conversion"
    ),
):
    """
    Convert cryptocurrency amounts between different currencies.

    Args:
        amount: The amount to convert (must be positive)
        from_currency: Source currency symbol (e.g., 'BTCUSDT')
        to_currency: Target currency symbol (e.g., 'ETHUSDT')
        timestamp: Optional ISO timestamp for historical conversion

    Returns:
        ConvertResponse with converted amount and rate information

    Raises:
        HTTPException: For various error conditions
    """
    try:
        # Normalize currency symbols
        from_symbol = from_currency.upper()
        to_symbol = to_currency.upper()

        # Validate that we're not doing cross-currency conversion
        if not _is_direct_pair(from_symbol, to_symbol):
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error="unsupported_conversion",
                    message=f"Cross-currency conversion from {from_symbol} to {to_symbol} is not supported",
                ).model_dump(),
            )

        # Parse timestamp if provided
        target_timestamp = None
        if timestamp:
            try:
                target_timestamp = datetime.fromisoformat(
                    timestamp.replace("Z", "+00:00")
                )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=ErrorResponse(
                        error="invalid_timestamp",
                        message="Timestamp must be in ISO format",
                    ).model_dump(),
                )

        # Get conversion rate
        if not storage:
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="storage_not_initialized",
                    message="Storage is not properly initialized",
                ).model_dump(),
            )

        rate_info = await storage.get_conversion_rate(
            from_symbol, to_symbol, target_timestamp
        )

        if rate_info is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="quotes_not_found",
                    message=f"No quotes available for conversion from {from_symbol} to {to_symbol}",
                ).model_dump(),
            )

        # Check for errors in rate info
        if "error" in rate_info:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error=rate_info["error"], message=rate_info["message"]
                ).model_dump(),
            )

        # Calculate conversion
        rate = rate_info["rate"]
        converted_amount = amount * rate
        quote_timestamp = rate_info["from_quote"].timestamp

        return ConvertResponse(
            amount=amount,
            from_currency=from_symbol,
            to_currency=to_symbol,
            converted_amount=converted_amount,
            rate=rate,
            timestamp=quote_timestamp,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in conversion: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="internal_error",
                message="An unexpected error occurred during conversion",
            ).model_dump(),
        )


def _is_direct_pair(from_symbol: str, to_symbol: str) -> bool:
    """
    Check if the conversion is a direct pair (not cross-currency).
    For simplicity, we only support conversions where both currencies
    share a common base (e.g., BTCUSDT -> ETHUSDT via USDT).
    """
    # Extract base currencies
    common_bases = ["USDT", "BTC", "ETH", "BNB"]

    for base in common_bases:
        if from_symbol.endswith(base) and to_symbol.endswith(base):
            return True

    return False


@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            error="not_found", message="Endpoint not found"
        ).model_dump(),
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_error", message="An internal server error occurred"
        ).model_dump(),
    )


async def main():
    """Main entry point for the API server."""
    # Set up logging
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run the server
    config = uvicorn.Config(
        app,
        host=Config.API_HOST,
        port=Config.API_PORT,
        log_level=Config.LOG_LEVEL.lower(),
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
