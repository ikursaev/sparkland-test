# Crypto Converter

A cryptocurrency conversion API that provides real-time currency conversion using live quotes from Binance exchange.

## Project Overview

The Crypto Converter consists of two main components that run as separate processes:

1. **Currency Conversion API** - A FastAPI-based REST API that provides currency conversion endpoints
2. **Quote Consumer** - A WebSocket client that fetches real-time quotes from Binance and stores them

## Features

- **Real-time Currency Conversion**: Convert between cryptocurrencies using live market rates
- **WebSocket Integration**: Real-time quote updates from Binance exchange
- **Historical Data Support**: Optional timestamp parameter for historical conversions
- **Quote Freshness Validation**: Ensures quotes are not older than 1 minute for live conversions
- **Automatic Data Cleanup**: Removes quotes older than 7 days
- **Docker Support**: Easy deployment with docker-compose
- **Comprehensive Testing**: Unit tests and integration tests included
- **Error Handling**: Proper error responses for various scenarios

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Binance API   │    │ Quote Consumer  │    │ SQLite Database │
│  (WebSocket)    │───▶│                 │───▶│                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐            │
│   Client/User   │    │ Conversion API  │            │
│                 │◄───│                 │◄───────────┘
└─────────────────┘    └─────────────────┘
```

## Quick Start

### Using Docker (Recommended)

1. **Clone and setup the project:**
   ```bash
   git clone <repository-url>
   cd crypto-converter
   ```

2. **Start the services:**
   ```bash
   docker-compose up
   ```

3. **Test the API:**
   ```bash
   curl "http://localhost:8000/convert?amount=1&from=BTCUSDT&to=ETHUSDT"
   ```

### Manual Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Copy environment configuration:**
   ```bash
   cp .env.example .env
   ```

3. **Start the Quote Consumer:**
   ```bash
   python run.py quote-consumer
   ```

4. **In another terminal, start the API:**
   ```bash
   python run.py api
   ```

## API Documentation

### Base URL
```
http://localhost:8000
```

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

**Example Request:**
```bash
curl "http://localhost:8000/convert?amount=1.5&from=BTCUSDT&to=ETHUSDT"
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

## Configuration

All configuration is done through environment variables. See `.env.example` for available options:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `./quotes.db` | SQLite database file path |
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `8000` | API server port |
| `BINANCE_WS_URL` | WebSocket URL | Binance WebSocket endpoint |
| `QUOTE_SAVE_INTERVAL` | `30` | Quote save interval (seconds) |
| `QUOTE_RETENTION_DAYS` | `7` | Quote retention period (days) |
| `LOG_LEVEL` | `INFO` | Logging level |

## Supported Currency Pairs

The system supports direct conversions between currencies that share a common base:

- **USDT-based pairs**: BTCUSDT ↔ ETHUSDT, BTCUSDT ↔ ADAUSDT, etc.
- **BTC-based pairs**: ETHBTC ↔ ADABTC, etc.
- **ETH-based pairs**: ADAETH ↔ BNBETH, etc.

Cross-currency conversions (e.g., BTCUSDT → LTCETH) are not supported to keep the implementation simple.

## Development

### Project Structure
```
crypto_converter/
├── api/                 # FastAPI application
│   ├── __init__.py
│   └── service.py
├── quote_consumer/      # Quote consumer service
│   ├── __init__.py
│   └── service.py
└── shared/              # Shared components
    ├── __init__.py
    ├── config.py        # Configuration management
    ├── models.py        # Data models
    └── storage.py       # Database interface
tests/                   # Test suite
├── __init__.py
├── conftest.py         # Test configuration
├── test_api.py         # API tests
├── test_storage.py     # Storage tests
└── test_integration.py # Integration tests
run.py                  # Main entry point
requirements.txt        # Python dependencies
Dockerfile             # Docker image definition
docker-compose.yml     # Docker services configuration
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run with coverage
pytest --cov=crypto_converter

# Run specific test file
pytest tests/test_api.py -v
```

### Adding New Currency Pairs

To add support for new currency pairs:

1. Update the `BINANCE_WS_URL` in your environment configuration to include the new ticker symbols
2. The system will automatically start collecting quotes for the new pairs
3. Ensure the pairs follow the supported conversion logic in `_is_direct_pair()` function

### Logging

The application logs to both console and file (`crypto_converter.log`). Log levels can be controlled via the `LOG_LEVEL` environment variable.

## Troubleshooting

### Common Issues

**Quote Consumer not connecting:**
- Check internet connectivity
- Verify Binance WebSocket URL is accessible
- Check firewall settings

**API returning "quotes_not_found":**
- Ensure Quote Consumer is running and collecting data
- Wait a few minutes for initial quote collection
- Check database file exists and is writable

**API returning "quotes_outdated":**
- Verify Quote Consumer is actively receiving updates
- Check WebSocket connection status
- Ensure system time is synchronized

**Docker containers not starting:**
- Check Docker and docker-compose are installed
- Verify port 8000 is not in use
- Check container logs: `docker-compose logs`

### Performance Considerations

- The SQLite database is suitable for development and moderate production use
- For high-volume production deployments, consider migrating to PostgreSQL or MySQL
- Quote Consumer memory usage is minimal as quotes are periodically saved and buffered data is cleared
- API response time is typically under 50ms for cached quote lookups

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `pytest`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational and development purposes. Do not use in production without proper testing and security review. Cryptocurrency trading involves risk, and this tool should not be used for actual financial decisions without proper validation.
