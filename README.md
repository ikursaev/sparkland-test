# Crypto Converter

A cryptocurrency conversion API that provides real-time currency conversion using live quotes from Binance exchange.

## Project Overview

The Crypto Converter consists of two main components that run as separate processes:

1. **Currency Conversion API** - A FastAPI-based REST API that provides currency conversion endpoints
2. **Quote Consumer** - A WebSocket client that fetches real-time quotes from Binance and stores them

## Features

- **Real-time Currency Conversion**: Convert between cryptocurrencies using live market rates
- **Historical Conversions**: Convert using quotes from specific dates with the timestamp parameter
- **Comprehensive Symbol Coverage**: Automatically fetches and supports ALL active trading pairs from Binance (~2,600 symbols)
- **REST API Integration**: Reliable quote updates using Binance REST API with configurable polling intervals
- **Quote Freshness Validation**: Ensures quotes are not older than 1 minute for live conversions
- **Timezone-Aware Storage**: All quotes stored in UTC with proper timezone handling
- **Automatic Data Cleanup**: Removes quotes older than 7 days
- **Docker Support**: Easy deployment with docker-compose
- **Comprehensive Testing**: Unit tests and integration tests included
- **Error Handling**: Proper error responses for various scenarios

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Binance API   │    │ Quote Consumer  │    │ SQLite Database │
│   (REST API)    │───>│                 │───>│                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐              │
│   Client/User   │    │ Conversion API  │              │
│                 │<───│                 │<─────────────┘
└─────────────────┘    └─────────────────┘
```

## Quick Start

### Using Docker (Recommended)

1. **Clone and setup the project:**
   ```bash
   git clone <repository-url>
   cd crypto-converter
   ```

2. **Copy and edit environment configuration:**
   ```bash
   cp .env.example .env
   ```

3. **Start the services:**
   ```bash
   docker-compose up
   ```

### Manual Installation

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Copy and edit environment configuration:**
   ```bash
   cp .env.example .env
   ```

3. **Start the Quote Consumer:**
   ```bash
   uv run python run.py quote-consumer
   ```

4. **In another terminal, start the API:**
   ```bash
   uv run python run.py api
   ```

## API Documentation

### Base URL
```
http://localhost:{API_PORT}
```
*Default port is 8000, but can be configured via the API_PORT environment variable.*
*For Docker deployments, the API_HOST should remain 0.0.0.0 to accept connections from outside the container.*

### Endpoints

#### Health Check
```http
GET /
```

**Response:**
```json
{
  "message": "Crypto Converter API is running",
  "status": "healthy"
}
```

#### Currency Conversion
```http
GET /convert?amount={amount}&from={from_currency}&to={to_currency}[&timestamp={iso_timestamp}]
```

**Parameters:**
- `amount` (required): Amount to convert (positive number)
- `from` (required): Source currency symbol (e.g., "BTCUSDT")
- `to` (required): Target currency symbol (e.g., "ETHUSDT")
- `timestamp` (optional): ISO format timestamp for historical conversion

**Live Conversion Example:**
```bash
curl "http://localhost:${API_PORT:-8000}/convert?amount=1.5&from=BTCUSDT&to=ETHUSDT"
```

**Historical Conversion Example:**
```bash
curl "http://localhost:${API_PORT:-8000}/convert?amount=1&from=BTCUSDT&to=ETHUSDT&timestamp=2025-08-12T15:30:00"
```

**Success Response:**
```json
{
  "amount": 1.5,
  "from_currency": "BTCUSDT",
  "to_currency": "ETHUSDT",
  "converted_amount": 22.5,
  "rate": 15.0,
  "timestamp": "2024-01-15T10:30:00"
}
```

**Error Responses:**

*Quotes not found:*
```json
{
  "error": "quotes_not_found",
  "message": "No quotes available for conversion from BTCUSDT to ETHUSDT"
}
```

*Quotes outdated:*
```json
{
  "error": "quotes_outdated",
  "message": "Quotes are older than 1 minute"
}
```

*Unsupported conversion:*
```json
{
  "error": "unsupported_conversion",
  "message": "Cross-currency conversion from BTCUSDT to LTCETH is not supported"
}
```

### Historical Conversions (Timestamp Feature)

The API supports historical conversions using the optional `timestamp` parameter. This feature allows you to get conversion rates using quotes from a specific day.

#### How It Works

- **UTC Storage**: All quotes are stored with UTC timestamps for consistency
- **Day-Based Retrieval**: When a timestamp is provided, the API finds the last available quote from that specific day
- **Timezone Awareness**: The system properly handles timezone differences

#### Timestamp Format

Use ISO 8601 format for timestamps:
- `YYYY-MM-DDTHH:MM:SS` (e.g., `2025-08-12T15:30:00`)
- `YYYY-MM-DDTHH:MM:SSZ` (with explicit UTC timezone)
- `YYYY-MM-DDTHH:MM:SS+00:00` (with timezone offset)

#### Examples

**Get conversion rate from a specific day:**
```bash
curl "http://localhost:8000/convert?amount=100&from=ETHUSDT&to=BNBUSDT&timestamp=2025-08-12T12:00:00"
```

**Response includes the actual timestamp of the quote used:**
```json
{
  "amount": 100.0,
  "from_currency": "ETHUSDT",
  "to_currency": "BNBUSDT",
  "converted_amount": 549.02,
  "rate": 5.4902,
  "timestamp": "2025-08-12T22:34:03.171547+00:00"
}
```

#### Important Notes

- **Data Availability**: Historical data is only available for days when quotes were collected
- **UTC Time**: The system stores quotes in UTC time, so be aware of timezone differences
- **Quote Retention**: Quotes older than 7 days are automatically cleaned up
- **Last Quote of Day**: The API returns the last available quote from the requested day

#### Timezone Considerations

If your local time is ahead of UTC, be aware that:
- Quotes are stored with UTC timestamps
- A request for "today" might not find data if it's still "yesterday" in UTC
- Always check the `timestamp` field in the response to see which quote was actually used

**Example timezone scenario:**
- Your local time: `2025-08-13 01:30` (UTC+3)
- UTC time: `2025-08-12 22:30`
- Quotes exist for: `2025-08-12` (UTC)
- Request for `2025-08-13T12:00:00`: ❌ No data (future UTC date)
- Request for `2025-08-12T12:00:00`: ✅ Returns last quote from August 12

## Configuration

All configuration is done through environment variables. See `.env.example` for available options.

**Both Docker and manual installations use the same `.env` file for configuration.**

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `./quotes.db` | SQLite database file path |
| `API_HOST` | `0.0.0.0` | API server host (use `0.0.0.0` for Docker, `127.0.0.1` for local-only) |
| `API_PORT` | `8000` | API server port |
| `BINANCE_REST_URL` | `https://api.binance.com` | Binance REST API base URL |
| `HTTP_POLLING_INTERVAL` | `10` | Quote fetching interval (seconds) |
| `QUOTE_SAVE_INTERVAL` | `30` | Quote save interval (seconds) |
| `QUOTE_RETENTION_DAYS` | `7` | Quote retention period (days) |
| `LOG_LEVEL` | `INFO` | Logging level |

## Supported Currency Pairs

The system automatically fetches and supports **ALL active trading pairs from Binance** (currently ~2,600 symbols), including:

- **USDT-based pairs**: 537+ pairs (BTCUSDT, ETHUSDT, ADAUSDT, etc.)
- **BTC-based pairs**: 376+ pairs (ETHBTC, ADABTC, etc.)
- **Other base currencies**: ETH, BNB, FDUSD, and many more

The system supports direct conversions between currencies that share a common base currency:
- BTCUSDT ↔ ETHUSDT ↔ ADAUSDT (all share USDT base)
- ETHBTC ↔ ADABTC (both share BTC base)

Cross-currency conversions (e.g., BTCUSDT → LTCETH) are not supported to keep the implementation simple.

### Automatic Symbol Discovery

The system automatically:
1. Fetches all active trading symbols from Binance's `exchangeInfo` API
2. Collects real-time quotes for all discovered symbols
3. No manual configuration of symbol lists is required

