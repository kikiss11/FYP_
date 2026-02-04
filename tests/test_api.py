"""Tests for the FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.main import app
from src import __version__


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Tests for health endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Google Trends Scraper API"
        assert "version" in data

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == __version__


class TestTrendsEndpoints:
    """Tests for trends data endpoints."""

    def test_get_config(self, client):
        """Test config endpoint returns configuration."""
        response = client.get("/trends/config")
        assert response.status_code == 200
        data = response.json()
        assert "keywords" in data
        assert "regions" in data
        assert "timeframe" in data

    @patch("src.api.routes.get_db")
    def test_interest_over_time_empty(self, mock_db, client):
        """Test interest over time with no data."""
        # Mock empty database
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_session.query.return_value = mock_query
        mock_db.return_value = iter([mock_session])

        response = client.get("/trends/interest-over-time")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


class TestSchedulerEndpoints:
    """Tests for scheduler endpoints."""

    @patch("src.api.routes.get_scheduler")
    def test_scheduler_status(self, mock_get_scheduler, client):
        """Test scheduler status endpoint."""
        mock_scheduler = MagicMock()
        mock_scheduler.get_status.return_value = {
            "running": False,
            "next_run": None,
            "schedule": {
                "day_of_week": "sunday",
                "hour": 2,
                "minute": 0,
            },
        }
        mock_get_scheduler.return_value = mock_scheduler

        response = client.get("/scheduler/status")
        assert response.status_code == 200
        data = response.json()
        assert "running" in data
        assert "schedule" in data


class TestJobsEndpoints:
    """Tests for jobs endpoints."""

    @patch("src.api.routes.get_db")
    def test_list_jobs_empty(self, mock_db, client):
        """Test listing jobs when empty."""
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_session.query.return_value = mock_query
        mock_db.return_value = iter([mock_session])

        response = client.get("/jobs")
        assert response.status_code == 200
        assert response.json() == []


class TestAPIDocumentation:
    """Tests for API documentation."""

    def test_openapi_available(self, client):
        """Test OpenAPI spec is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data

    def test_docs_available(self, client):
        """Test Swagger docs are available."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_available(self, client):
        """Test ReDoc is available."""
        response = client.get("/redoc")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

