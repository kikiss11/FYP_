"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ===== Request Schemas =====

class ExtractionRequest(BaseModel):
    """Request body for triggering extraction."""

    keywords: Optional[list[str]] = Field(
        default=None,
        description="Keywords to scrape (uses config if not provided)",
        example=["pant", "dress", "t-shirt"],
    )
    regions: Optional[list[str]] = Field(
        default=None,
        description="Region codes to scrape (uses config if not provided)",
        example=["HK", "US", "GB"],
    )
    save_to_db: bool = Field(default=True, description="Save results to database")
    save_to_csv: bool = Field(default=True, description="Export results to CSV")


# ===== Response Schemas =====

class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    timestamp: datetime


class SchedulerStatus(BaseModel):
    """Scheduler status response."""

    running: bool
    next_run: Optional[str]
    schedule: dict


class ExtractionJobResponse(BaseModel):
    """Response for extraction job."""

    job_id: int
    status: str
    keywords: list[str]
    regions: list[str]
    total_combinations: int
    errors: int


class TrendDataResponse(BaseModel):
    """Single trend data point."""

    id: int
    keyword: str
    region_code: str
    region_name: str
    date: datetime
    interest: int
    is_partial: bool


class RelatedQueryResponse(BaseModel):
    """Related query response."""

    id: int
    keyword: str
    region_code: str
    query_type: str
    query_text: str
    value: Optional[int]
    link: Optional[str]


class RelatedTopicResponse(BaseModel):
    """Related topic response."""

    id: int
    keyword: str
    region_code: str
    topic_type: str
    topic_title: str
    topic_mid: Optional[str]
    topic_category: Optional[str]
    value: Optional[int]
    link: Optional[str]


class JobSummaryResponse(BaseModel):
    """Scrape job summary."""

    id: int
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    keywords_count: int
    regions_count: int
    error_message: Optional[str]


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""

    total: int
    page: int
    per_page: int
    pages: int
    items: list


class KeywordStatsResponse(BaseModel):
    """Statistics for a keyword."""

    keyword: str
    total_data_points: int
    regions_covered: int
    latest_extraction: Optional[datetime]
    avg_interest: Optional[float]


class RegionStatsResponse(BaseModel):
    """Statistics for a region."""

    region_code: str
    region_name: str
    keywords_tracked: int
    total_data_points: int
    latest_extraction: Optional[datetime]

