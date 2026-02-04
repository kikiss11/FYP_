"""Configuration management for Google Trends Scraper."""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "google-trends-scraper"
    app_env: str = "development"
    debug: bool = True

    # Database
    database_url: str = "sqlite:///./data/trends.db"

    # Redis (optional)
    redis_url: Optional[str] = None

    # Google Trends
    trends_language: str = "en-US"
    trends_timezone: int = 480  # Hong Kong timezone
    request_delay: int = 15  # Seconds between requests (avoid rate limiting)

    # Scheduler
    scheduler_enabled: bool = True
    schedule_day_of_week: str = "sunday"
    schedule_hour: int = 2
    schedule_minute: int = 0

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True

    # Dashboard
    dashboard_port: int = 8501

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


class TrendsConfig:
    """Google Trends scraping configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(__file__).parent.parent / "config.yaml"
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return self._default_config()

    @staticmethod
    def _default_config() -> dict:
        """Return default configuration."""
        return {
            "keywords": ["pant", "dress", "t-shirt"],
            "regions": [
                {"code": "HK", "name": "Hong Kong"},
                {"code": "US", "name": "United States"},
                {"code": "GB", "name": "United Kingdom"},
                {"code": "TW", "name": "Taiwan"},
                {"code": "SG", "name": "Singapore"},
            ],
            "timeframe": "today 3-m",  # Last 3 months
            "category": 0,  # All categories
            "property": "",  # Web Search
        }

    @property
    def keywords(self) -> list[str]:
        """Get configured keywords."""
        return self._config.get("keywords", ["pant", "dress", "t-shirt"])

    @property
    def regions(self) -> list[dict]:
        """Get configured regions."""
        return self._config.get(
            "regions",
            [
                {"code": "HK", "name": "Hong Kong"},
                {"code": "US", "name": "United States"},
            ],
        )

    @property
    def region_codes(self) -> list[str]:
        """Get region codes only."""
        return [r["code"] for r in self.regions]

    @property
    def timeframe(self) -> str:
        """Get timeframe for queries."""
        return self._config.get("timeframe", "today 3-m")

    @property
    def category(self) -> int:
        """Get category filter."""
        return self._config.get("category", 0)

    @property
    def property(self) -> str:
        """Get property filter (web, news, images, youtube, froogle)."""
        return self._config.get("property", "")


# Global instances
settings = Settings()
trends_config = TrendsConfig()

