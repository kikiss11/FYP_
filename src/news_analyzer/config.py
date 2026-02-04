"""Configuration for Tariff News Analyzer."""

from typing import Optional
from pydantic_settings import BaseSettings


class NewsAnalyzerSettings(BaseSettings):
    """News analyzer settings."""

    # NewsAPI.org (free tier: 100 requests/day)
    newsapi_key: Optional[str] = None

    # GNews API (free tier: 100 requests/day)
    gnews_api_key: Optional[str] = None

    # Request settings
    news_request_delay: int = 2  # Seconds between requests
    max_articles_per_source: int = 100

    # Analysis settings
    sentiment_model: str = "ProsusAI/finbert"  # Financial sentiment model
    ner_model: str = "en_core_web_sm"  # spaCy NER model

    # Scheduler
    news_schedule_enabled: bool = True
    news_schedule_hour: int = 6  # Run at 6 AM daily

    class Config:
        env_file = ".env"
        case_sensitive = False


# Tariff-related search queries by region
TARIFF_QUERIES = {
    "global": [
        "tariff trade war",
        "import tariff increase",
        "export restrictions",
        "trade sanctions",
        "customs duties",
        "trade agreement",
        "trade negotiation",
        "trade tension",
        "trade conflict",
        "trade barrier",
    ],
    "US": [
        "US tariff China",
        "US trade policy",
        "US import duties",
        "Section 301 tariff",
        "US trade deficit",
        "Buy American Act",
    ],
    "CN": [
        "China tariff retaliation",
        "China trade war",
        "China export controls",
        "China rare earth",
        "Made in China 2025",
    ],
    "EU": [
        "EU tariff",
        "European trade policy",
        "EU anti-dumping",
        "EU carbon border tax",
        "Brexit trade",
    ],
    "ASIA": [
        "Asia trade agreement",
        "RCEP trade",
        "ASEAN tariff",
        "Japan trade",
        "Korea trade",
        "Taiwan trade",
    ],
}

# Countries/regions to analyze
ANALYSIS_REGIONS = [
    {"code": "US", "name": "United States", "keywords": ["United States", "US", "USA", "American"]},
    {"code": "CN", "name": "China", "keywords": ["China", "Chinese", "Beijing", "PRC"]},
    {"code": "EU", "name": "European Union", "keywords": ["European Union", "EU", "Europe", "Brussels"]},
    {"code": "GB", "name": "United Kingdom", "keywords": ["United Kingdom", "UK", "Britain", "British"]},
    {"code": "JP", "name": "Japan", "keywords": ["Japan", "Japanese", "Tokyo"]},
    {"code": "KR", "name": "South Korea", "keywords": ["South Korea", "Korea", "Seoul", "Korean"]},
    {"code": "TW", "name": "Taiwan", "keywords": ["Taiwan", "Taiwanese", "Taipei"]},
    {"code": "IN", "name": "India", "keywords": ["India", "Indian", "New Delhi"]},
    {"code": "DE", "name": "Germany", "keywords": ["Germany", "German", "Berlin"]},
    {"code": "MX", "name": "Mexico", "keywords": ["Mexico", "Mexican"]},
    {"code": "CA", "name": "Canada", "keywords": ["Canada", "Canadian", "Ottawa"]},
    {"code": "AU", "name": "Australia", "keywords": ["Australia", "Australian"]},
    {"code": "BR", "name": "Brazil", "keywords": ["Brazil", "Brazilian"]},
    {"code": "VN", "name": "Vietnam", "keywords": ["Vietnam", "Vietnamese"]},
    {"code": "HK", "name": "Hong Kong", "keywords": ["Hong Kong", "HK"]},
    {"code": "SG", "name": "Singapore", "keywords": ["Singapore"]},
]

# Trade tension indicators
TENSION_KEYWORDS = {
    "high_tension": [
        "trade war", "retaliation", "sanctions", "ban", "blacklist",
        "escalation", "conflict", "dispute", "punitive", "countermeasures",
        "embargo", "restriction", "prohibited", "blocked", "suspended",
    ],
    "moderate_tension": [
        "tariff increase", "investigation", "anti-dumping", "complaint",
        "tension", "concern", "warning", "threat", "review", "probe",
        "uncertainty", "dispute", "challenge", "pressure",
    ],
    "low_tension": [
        "negotiation", "talks", "discussion", "dialogue", "meeting",
        "cooperation", "agreement", "deal", "partnership", "resolution",
    ],
    "positive": [
        "trade deal", "agreement signed", "tariff reduction", "exemption",
        "cooperation", "partnership", "free trade", "lifted", "resolved",
        "breakthrough", "progress", "improvement",
    ],
}

# Trade effectiveness indicators
EFFECTIVENESS_KEYWORDS = {
    "positive_impact": [
        "export growth", "trade surplus", "market access", "competitive advantage",
        "investment increase", "job creation", "economic growth", "market share",
        "revenue increase", "profit margin", "supply chain", "diversification",
    ],
    "negative_impact": [
        "export decline", "trade deficit", "market loss", "cost increase",
        "supply shortage", "price increase", "job loss", "factory closure",
        "bankruptcy", "recession", "inflation", "disruption",
    ],
}

news_settings = NewsAnalyzerSettings()
