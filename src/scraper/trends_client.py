"""Google Trends API client wrapper."""

import time
from dataclasses import dataclass
from typing import Any, Optional

import pandas as pd
from loguru import logger
from pytrends.request import TrendReq

from ..config import settings, trends_config


@dataclass
class TrendsResult:
    """Container for trends query results."""

    keyword: str
    region_code: str
    region_name: str
    interest_over_time: Optional[pd.DataFrame] = None
    interest_by_region: Optional[pd.DataFrame] = None
    related_queries_top: Optional[pd.DataFrame] = None
    related_queries_rising: Optional[pd.DataFrame] = None
    related_topics_top: Optional[pd.DataFrame] = None
    related_topics_rising: Optional[pd.DataFrame] = None
    error: Optional[str] = None


class TrendsClient:
    """Client for interacting with Google Trends."""

    def __init__(
        self,
        hl: str = None,
        tz: int = None,
        timeout: tuple = (10, 30),
        retries: int = 5,
        backoff_factor: float = 1.0,
    ):
        """
        Initialize the Google Trends client.

        Args:
            hl: Language for results (default from settings)
            tz: Timezone offset in minutes (default from settings)
            timeout: Request timeout (connect, read)
            retries: Number of retry attempts
            backoff_factor: Backoff multiplier for retries
        """
        self.hl = hl or settings.trends_language
        self.tz = tz or settings.trends_timezone
        self.timeout = timeout
        self.retries = retries
        self.backoff_factor = backoff_factor
        self.request_delay = settings.request_delay
        self._request_count = 0

        self._client: Optional[TrendReq] = None
        self._init_client()

    def _init_client(self):
        """Initialize the pytrends client."""
        try:
            self._client = TrendReq(
                hl=self.hl,
                tz=self.tz,
                timeout=self.timeout,
                retries=self.retries,
                backoff_factor=self.backoff_factor,
            )
            logger.info(f"Initialized TrendReq client (lang={self.hl}, tz={self.tz})")
        except Exception as e:
            logger.error(f"Failed to initialize TrendReq client: {e}")
            raise

    def _smart_delay(self):
        """Apply smart delay to avoid rate limiting."""
        self._request_count += 1
        
        # Add extra delay every 5 requests
        if self._request_count % 5 == 0:
            extra_delay = 30  # Extra 30 seconds every 5 requests
            logger.info(f"Adding extra delay ({extra_delay}s) to avoid rate limiting...")
            time.sleep(extra_delay)
        
        self._smart_delay()

    def _build_payload(
        self,
        keywords: list[str],
        geo: str = "",
        timeframe: str = "today 3-m",
        category: int = 0,
        gprop: str = "",
    ):
        """Build the search payload."""
        try:
            self._client.build_payload(
                kw_list=keywords,
                cat=category,
                timeframe=timeframe,
                geo=geo,
                gprop=gprop,
            )
            logger.debug(f"Built payload: keywords={keywords}, geo={geo}")
        except Exception as e:
            logger.error(f"Failed to build payload: {e}")
            raise

    def get_interest_over_time(
        self,
        keyword: str,
        geo: str = "",
        timeframe: str = "today 3-m",
    ) -> pd.DataFrame:
        """
        Get interest over time for a keyword.

        Args:
            keyword: Search keyword
            geo: Region code (e.g., 'HK', 'US')
            timeframe: Time range (e.g., 'today 3-m', 'today 12-m')

        Returns:
            DataFrame with date and interest columns
        """
        self._build_payload([keyword], geo=geo, timeframe=timeframe)
        self._smart_delay()

        try:
            df = self._client.interest_over_time()
            if df.empty:
                logger.warning(f"No interest over time data for '{keyword}' in {geo}")
            return df
        except Exception as e:
            logger.error(f"Error getting interest over time: {e}")
            return pd.DataFrame()

    def get_interest_by_region(
        self,
        keyword: str,
        geo: str = "",
        resolution: str = "COUNTRY",
        inc_low_vol: bool = True,
    ) -> pd.DataFrame:
        """
        Get interest by sub-region.

        Args:
            keyword: Search keyword
            geo: Region code
            resolution: Resolution level (COUNTRY, REGION, CITY, DMA)
            inc_low_vol: Include low volume regions

        Returns:
            DataFrame with region and interest columns
        """
        self._build_payload([keyword], geo=geo)
        self._smart_delay()

        try:
            df = self._client.interest_by_region(
                resolution=resolution,
                inc_low_vol=inc_low_vol,
                inc_geo_code=True,
            )
            if df.empty:
                logger.warning(f"No interest by region data for '{keyword}' in {geo}")
            return df
        except Exception as e:
            logger.error(f"Error getting interest by region: {e}")
            return pd.DataFrame()

    def get_related_queries(
        self,
        keyword: str,
        geo: str = "",
        timeframe: str = "today 3-m",
    ) -> dict[str, pd.DataFrame]:
        """
        Get related search queries.

        Args:
            keyword: Search keyword
            geo: Region code
            timeframe: Time range

        Returns:
            Dict with 'top' and 'rising' DataFrames
        """
        self._build_payload([keyword], geo=geo, timeframe=timeframe)
        self._smart_delay()

        result = {"top": pd.DataFrame(), "rising": pd.DataFrame()}

        try:
            related = self._client.related_queries()
            if keyword in related:
                kw_data = related[keyword]
                if kw_data.get("top") is not None:
                    result["top"] = kw_data["top"]
                if kw_data.get("rising") is not None:
                    result["rising"] = kw_data["rising"]
            return result
        except Exception as e:
            logger.error(f"Error getting related queries: {e}")
            return result

    def get_related_topics(
        self,
        keyword: str,
        geo: str = "",
        timeframe: str = "today 3-m",
    ) -> dict[str, pd.DataFrame]:
        """
        Get related topics/themes.

        Args:
            keyword: Search keyword
            geo: Region code
            timeframe: Time range

        Returns:
            Dict with 'top' and 'rising' DataFrames
        """
        self._build_payload([keyword], geo=geo, timeframe=timeframe)
        self._smart_delay()

        result = {"top": pd.DataFrame(), "rising": pd.DataFrame()}

        try:
            related = self._client.related_topics()
            if keyword in related:
                kw_data = related[keyword]
                if kw_data.get("top") is not None:
                    result["top"] = kw_data["top"]
                if kw_data.get("rising") is not None:
                    result["rising"] = kw_data["rising"]
            return result
        except Exception as e:
            logger.error(f"Error getting related topics: {e}")
            return result

    def fetch_all_data(
        self,
        keyword: str,
        region_code: str,
        region_name: str,
        timeframe: str = None,
    ) -> TrendsResult:
        """
        Fetch all available data for a keyword-region combination.

        Args:
            keyword: Search keyword
            region_code: Region code (e.g., 'HK')
            region_name: Human-readable region name
            timeframe: Time range

        Returns:
            TrendsResult containing all data
        """
        timeframe = timeframe or trends_config.timeframe
        result = TrendsResult(
            keyword=keyword,
            region_code=region_code,
            region_name=region_name,
        )

        try:
            # Interest over time
            logger.info(f"Fetching interest over time: {keyword} ({region_code})")
            result.interest_over_time = self.get_interest_over_time(
                keyword, geo=region_code, timeframe=timeframe
            )

            # Interest by region
            logger.info(f"Fetching interest by region: {keyword} ({region_code})")
            result.interest_by_region = self.get_interest_by_region(
                keyword, geo=region_code
            )

            # Related queries
            logger.info(f"Fetching related queries: {keyword} ({region_code})")
            queries = self.get_related_queries(
                keyword, geo=region_code, timeframe=timeframe
            )
            result.related_queries_top = queries["top"]
            result.related_queries_rising = queries["rising"]

            # Related topics
            logger.info(f"Fetching related topics: {keyword} ({region_code})")
            topics = self.get_related_topics(
                keyword, geo=region_code, timeframe=timeframe
            )
            result.related_topics_top = topics["top"]
            result.related_topics_rising = topics["rising"]

            logger.success(f"Successfully fetched all data: {keyword} ({region_code})")

        except Exception as e:
            result.error = str(e)
            logger.error(f"Error fetching data for {keyword} ({region_code}): {e}")

        return result


# Singleton instance
_client: Optional[TrendsClient] = None


def get_trends_client() -> TrendsClient:
    """Get or create the trends client singleton."""
    global _client
    if _client is None:
        _client = TrendsClient()
    return _client

