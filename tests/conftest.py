"""
Test configuration for the crypto converter tests.
"""

import asyncio
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio

# Add project root to path before importing our modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import our modules after path setup
from crypto_converter.shared.models import Quote  # noqa: E402
from crypto_converter.shared.storage import QuoteStorage  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def temp_storage():
    """Create a temporary storage instance for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        storage = QuoteStorage(tmp.name)
        await storage.initialize()
        try:
            yield storage
        finally:
            await storage.close()
            # Wait a bit for Windows to release the file handle
            import asyncio

            await asyncio.sleep(0.1)
            try:
                os.unlink(tmp.name)
            except PermissionError:
                # On Windows, sometimes the file is still locked
                pass


@pytest.fixture
def sample_quotes():
    """Provide sample quotes for testing."""
    now = datetime.now(UTC)
    return [
        Quote(symbol="BTCUSDT", price=45000.0, timestamp=now),
        Quote(symbol="ETHUSDT", price=3000.0, timestamp=now),
        Quote(symbol="ADAUSDT", price=1.5, timestamp=now),
        Quote(symbol="BNBUSDT", price=400.0, timestamp=now),
    ]
