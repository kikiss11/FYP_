"""News scraper for tariff and trade news from multiple sources."""

import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

import httpx
from loguru import logger

from .config import (
    news_settings,
    TARIFF_QUERIES,
    ANALYSIS_REGIONS,
)
from .models import NewsArticle
from ..models import SessionLocal


class NewsScraper:
    """Multi-source news scraper for tariff and trade news."""

    def __init__(self):
        """Initialize the news scraper."""
        self.newsapi_key = news_settings.newsapi_key
        self.gnews_key = news_settings.gnews_api_key
        self.request_delay = news_settings.news_request_delay
        self.max_articles = news_settings.max_articles_per_source

        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )

    def _save_article(self, db, article_data: Dict[str, Any]) -> Optional[NewsArticle]:
        """Save article to database if not exists."""
        try:
            # Check if article already exists
            existing = db.query(NewsArticle).filter(
                NewsArticle.url == article_data["url"]
            ).first()

            if existing:
                logger.debug(f"Article already exists: {article_data['title'][:50]}")
                return None

            article = NewsArticle(**article_data)
            db.add(article)
            db.commit()
            db.refresh(article)
            logger.info(f"Saved article: {article.title[:50]}...")
            return article

        except Exception as e:
            db.rollback()
            logger.error(f"Error saving article: {e}")
            return None

    def fetch_newsapi(
        self,
        query: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        language: str = "en",
        sort_by: str = "relevancy",
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Fetch news from NewsAPI.org.

        Args:
            query: Search query
            from_date: Start date for articles
            to_date: End date for articles
            language: Article language
            sort_by: Sort order (relevancy, popularity, publishedAt)
            page_size: Number of articles per page

        Returns:
            List of article dictionaries
        """
        if not self.newsapi_key:
            logger.warning("NewsAPI key not configured. Set NEWSAPI_KEY in .env")
            return []

        articles = []
        url = "https://newsapi.org/v2/everything"

        # Default date range: last 7 days
        if not from_date:
            from_date = datetime.utcnow() - timedelta(days=7)
        if not to_date:
            to_date = datetime.utcnow()

        params = {
            "q": query,
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"),
            "language": language,
            "sortBy": sort_by,
            "pageSize": min(page_size, 100),
            "apiKey": self.newsapi_key,
        }

        try:
            response = self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "ok":
                for item in data.get("articles", []):
                    articles.append({
                        "source": "newsapi",
                        "source_name": item.get("source", {}).get("name"),
                        "author": item.get("author"),
                        "title": item.get("title"),
                        "description": item.get("description"),
                        "content": item.get("content"),
                        "url": item.get("url"),
                        "url_to_image": item.get("urlToImage"),
                        "published_at": datetime.fromisoformat(
                            item.get("publishedAt", "").replace("Z", "+00:00")
                        ),
                        "language": language,
                        "search_query": query,
                    })
                logger.info(f"NewsAPI: Found {len(articles)} articles for '{query}'")
            else:
                logger.warning(f"NewsAPI error: {data.get('message')}")

        except Exception as e:
            logger.error(f"NewsAPI request failed: {e}")

        time.sleep(self.request_delay)
        return articles

    def fetch_gnews(
        self,
        query: str,
        country: Optional[str] = None,
        language: str = "en",
        max_results: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Fetch news from GNews API.

        Args:
            query: Search query
            country: Country code (e.g., 'us', 'gb')
            language: Article language
            max_results: Maximum number of results

        Returns:
            List of article dictionaries
        """
        if not self.gnews_key:
            logger.warning("GNews API key not configured. Set GNEWS_API_KEY in .env")
            return []

        articles = []
        url = "https://gnews.io/api/v4/search"

        params = {
            "q": query,
            "lang": language,
            "max": min(max_results, 100),
            "apikey": self.gnews_key,
        }
        if country:
            params["country"] = country.lower()

        try:
            response = self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            for item in data.get("articles", []):
                articles.append({
                    "source": "gnews",
                    "source_name": item.get("source", {}).get("name"),
                    "author": None,
                    "title": item.get("title"),
                    "description": item.get("description"),
                    "content": item.get("content"),
                    "url": item.get("url"),
                    "url_to_image": item.get("image"),
                    "published_at": datetime.fromisoformat(
                        item.get("publishedAt", "").replace("Z", "+00:00")
                    ),
                    "language": language,
                    "search_query": query,
                    "search_region": country,
                })
            logger.info(f"GNews: Found {len(articles)} articles for '{query}'")

        except Exception as e:
            logger.error(f"GNews request failed: {e}")

        time.sleep(self.request_delay)
        return articles

    def fetch_google_news_rss(
        self,
        query: str,
        region: Optional[str] = None,
        language: str = "en",
    ) -> List[Dict[str, Any]]:
        """
        Fetch news from Google News RSS feed (no API key needed).

        Args:
            query: Search query
            region: Country code
            language: Language code

        Returns:
            List of article dictionaries
        """
        articles = []
        encoded_query = quote_plus(query)

        # Build Google News RSS URL (use simple format for better compatibility)
        # Google News RSS works best with US locale
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

        try:
            response = self.client.get(url)
            response.raise_for_status()

            # Parse RSS XML
            root = ET.fromstring(response.content)

            for item in root.findall(".//item"):
                title = item.find("title")
                link = item.find("link")
                pub_date = item.find("pubDate")
                source = item.find("source")
                description = item.find("description")

                if title is not None and link is not None:
                    # Parse publication date
                    pub_datetime = datetime.utcnow()
                    if pub_date is not None and pub_date.text:
                        try:
                            from email.utils import parsedate_to_datetime
                            pub_datetime = parsedate_to_datetime(pub_date.text)
                        except Exception:
                            pass

                    articles.append({
                        "source": "google_news_rss",
                        "source_name": source.text if source is not None else None,
                        "author": None,
                        "title": title.text,
                        "description": description.text if description is not None else None,
                        "content": None,
                        "url": link.text,
                        "url_to_image": None,
                        "published_at": pub_datetime,
                        "language": language,
                        "search_query": query,
                        "search_region": region,
                    })

            logger.info(f"Google News RSS: Found {len(articles)} articles for '{query}'")

        except Exception as e:
            logger.error(f"Google News RSS request failed: {e}")

        time.sleep(self.request_delay)
        return articles

    def fetch_all_sources(
        self,
        queries: Optional[List[str]] = None,
        regions: Optional[List[str]] = None,
        days_back: int = 7,
    ) -> Dict[str, int]:
        """
        Fetch news from all configured sources.

        Args:
            queries: List of search queries (defaults to tariff queries)
            regions: List of region codes to search
            days_back: Number of days to look back

        Returns:
            Dictionary with counts per source
        """
        db = SessionLocal()
        counts = {
            "newsapi": 0,
            "gnews": 0,
            "google_news_rss": 0,
            "total": 0,
            "saved": 0,
        }

        # Default queries
        if not queries:
            queries = TARIFF_QUERIES.get("global", [])[:5]  # Limit to top 5 queries

        # Default regions
        if not regions:
            regions = [r["code"] for r in ANALYSIS_REGIONS[:5]]  # Top 5 regions

        from_date = datetime.utcnow() - timedelta(days=days_back)

        try:
            for query in queries:
                logger.info(f"Fetching news for query: '{query}'")

                # NewsAPI (global search)
                if self.newsapi_key:
                    articles = self.fetch_newsapi(query, from_date=from_date)
                    counts["newsapi"] += len(articles)
                    for article_data in articles:
                        if self._save_article(db, article_data):
                            counts["saved"] += 1

                # GNews and Google News RSS (by region)
                for region in regions:
                    # GNews
                    if self.gnews_key:
                        articles = self.fetch_gnews(query, country=region)
                        counts["gnews"] += len(articles)
                        for article_data in articles:
                            if self._save_article(db, article_data):
                                counts["saved"] += 1

                    # Google News RSS (always available)
                    articles = self.fetch_google_news_rss(query, region=region)
                    counts["google_news_rss"] += len(articles)
                    for article_data in articles:
                        if self._save_article(db, article_data):
                            counts["saved"] += 1

            counts["total"] = counts["newsapi"] + counts["gnews"] + counts["google_news_rss"]

        finally:
            db.close()

        logger.info(f"News fetch completed: {counts}")
        return counts

    def fetch_tariff_news(
        self,
        regions: Optional[List[str]] = None,
        days_back: int = 7,
    ) -> Dict[str, int]:
        """
        Fetch tariff and trade news for analysis.

        Args:
            regions: List of region codes
            days_back: Number of days to look back

        Returns:
            Dictionary with fetch statistics
        """
        all_queries = []

        # Add global queries
        all_queries.extend(TARIFF_QUERIES.get("global", [])[:3])

        # Add region-specific queries
        if regions:
            for region in regions:
                region_queries = TARIFF_QUERIES.get(region, [])
                all_queries.extend(region_queries[:2])
        else:
            # Default: add US, CN, EU queries
            for key in ["US", "CN", "EU"]:
                all_queries.extend(TARIFF_QUERIES.get(key, [])[:2])

        # Remove duplicates while preserving order
        unique_queries = list(dict.fromkeys(all_queries))

        return self.fetch_all_sources(
            queries=unique_queries,
            regions=regions,
            days_back=days_back,
        )

    def close(self):
        """Close the HTTP client."""
        self.client.close()
