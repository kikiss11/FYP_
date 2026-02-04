"""Google Trends Scraper module."""

from .trends_client import TrendsClient, get_trends_client
from .extractor import TrendsExtractor
from .scheduler import TrendsScheduler, get_scheduler

__all__ = [
    "TrendsClient",
    "TrendsExtractor",
    "TrendsScheduler",
    "get_trends_client",
    "get_scheduler",
]
