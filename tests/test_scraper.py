"""Tests for the scraper module."""

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd

from src.config import trends_config, Settings
from src.scraper.trends_client import TrendsClient, TrendsResult


class TestTrendsConfig:
    """Tests for TrendsConfig."""

    def test_default_keywords(self):
        """Test default keywords are set."""
        assert "pant" in trends_config.keywords
        assert "dress" in trends_config.keywords
        assert "t-shirt" in trends_config.keywords

    def test_default_regions(self):
        """Test default regions include HK."""
        region_codes = trends_config.region_codes
        assert "HK" in region_codes

    def test_timeframe(self):
        """Test default timeframe."""
        assert trends_config.timeframe is not None


class TestTrendsClient:
    """Tests for TrendsClient."""

    @patch("src.scraper.trends_client.TrendReq")
    def test_client_initialization(self, mock_trendreq):
        """Test client initializes correctly."""
        client = TrendsClient(hl="en-US", tz=480)
        mock_trendreq.assert_called_once()
        assert client.hl == "en-US"
        assert client.tz == 480

    @patch("src.scraper.trends_client.TrendReq")
    def test_fetch_all_data_returns_result(self, mock_trendreq):
        """Test fetch_all_data returns TrendsResult."""
        # Setup mock
        mock_instance = MagicMock()
        mock_trendreq.return_value = mock_instance

        # Mock API responses
        mock_instance.interest_over_time.return_value = pd.DataFrame({
            "pant": [50, 60, 70],
            "isPartial": [False, False, True],
        }, index=pd.date_range("2024-01-01", periods=3, freq="W"))

        mock_instance.interest_by_region.return_value = pd.DataFrame({
            "pant": [80, 60, 40],
        }, index=["Region A", "Region B", "Region C"])

        mock_instance.related_queries.return_value = {
            "pant": {
                "top": pd.DataFrame({"query": ["pants men", "pants women"], "value": [100, 80]}),
                "rising": pd.DataFrame({"query": ["cargo pants"], "value": [500]}),
            }
        }

        mock_instance.related_topics.return_value = {
            "pant": {
                "top": pd.DataFrame({"topic_title": ["Fashion"], "value": [100]}),
                "rising": pd.DataFrame({"topic_title": ["Streetwear"], "value": [200]}),
            }
        }

        # Execute
        client = TrendsClient()
        result = client.fetch_all_data(
            keyword="pant",
            region_code="HK",
            region_name="Hong Kong",
        )

        # Assert
        assert isinstance(result, TrendsResult)
        assert result.keyword == "pant"
        assert result.region_code == "HK"
        assert result.error is None

    @patch("src.scraper.trends_client.TrendReq")
    def test_fetch_all_data_handles_error(self, mock_trendreq):
        """Test fetch_all_data handles errors gracefully."""
        mock_instance = MagicMock()
        mock_trendreq.return_value = mock_instance
        mock_instance.interest_over_time.side_effect = Exception("API Error")

        client = TrendsClient()
        result = client.fetch_all_data(
            keyword="pant",
            region_code="HK",
            region_name="Hong Kong",
        )

        assert result.error is not None
        assert "API Error" in result.error


class TestTrendsResult:
    """Tests for TrendsResult dataclass."""

    def test_result_creation(self):
        """Test TrendsResult can be created."""
        result = TrendsResult(
            keyword="test",
            region_code="HK",
            region_name="Hong Kong",
        )
        assert result.keyword == "test"
        assert result.region_code == "HK"
        assert result.interest_over_time is None
        assert result.error is None


class TestSettings:
    """Tests for Settings."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()
        assert settings.app_name == "google-trends-scraper"
        assert settings.request_delay == 5
        assert settings.scheduler_enabled is True


@pytest.fixture
def sample_trend_data():
    """Fixture for sample trend data."""
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=12, freq="W"),
        "pant": [50, 55, 60, 58, 62, 70, 75, 72, 68, 65, 60, 58],
        "dress": [40, 42, 45, 50, 55, 60, 58, 55, 52, 48, 45, 42],
        "t-shirt": [60, 62, 65, 70, 75, 80, 85, 82, 78, 72, 68, 65],
    })


def test_sample_data_shape(sample_trend_data):
    """Test sample data has expected shape."""
    assert len(sample_trend_data) == 12
    assert "pant" in sample_trend_data.columns
    assert "dress" in sample_trend_data.columns
    assert "t-shirt" in sample_trend_data.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

