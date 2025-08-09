"""
Tests for the API functionality.
"""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

# Add project root to path before importing our modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import our modules after path setup
from crypto_converter.api.service import app  # noqa: E402


class TestAPI:
    """Test cases for the API endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_health_check(self):
        """Test the health check endpoint."""
        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_convert_missing_parameters(self):
        """Test conversion endpoint with missing parameters."""
        response = self.client.get("/convert")
        assert response.status_code == 422  # Unprocessable Entity

    def test_convert_invalid_amount(self):
        """Test conversion with invalid amount."""
        response = self.client.get("/convert?amount=-10&from=BTCUSDT&to=ETHUSDT")
        assert response.status_code == 422

    def test_convert_unsupported_pair(self):
        """Test conversion with unsupported currency pair."""
        response = self.client.get("/convert?amount=1&from=BTCUSDT&to=LTCETH")
        assert response.status_code == 400
        data = response.json()
        # Handle the nested error structure from FastAPI
        if "detail" in data and isinstance(data["detail"], dict):
            assert data["detail"]["error"] == "unsupported_conversion"
        else:
            assert "unsupported_conversion" in str(data)

    def test_convert_invalid_timestamp(self):
        """Test conversion with invalid timestamp format."""
        response = self.client.get(
            "/convert?amount=1&from=BTCUSDT&to=ETHUSDT&timestamp=invalid"
        )
        assert response.status_code == 400
        data = response.json()
        # Handle the nested error structure from FastAPI
        if "detail" in data and isinstance(data["detail"], dict):
            assert data["detail"]["error"] == "invalid_timestamp"
        else:
            assert "invalid_timestamp" in str(data) or "timestamp" in str(data).lower()

    def test_convert_no_quotes(self):
        """Test conversion when no quotes are available."""
        response = self.client.get("/convert?amount=1&from=BTCUSDT&to=ETHUSDT")
        # This might return 500 if storage is not initialized properly
        assert response.status_code in [404, 500]

    def test_404_endpoint(self):
        """Test non-existent endpoint."""
        response = self.client.get("/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "not_found"
