"""API route handlers."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import __version__
from ..config import trends_config
from ..models import (
    InterestByRegion,
    RelatedQuery,
    RelatedTopic,
    ScrapeJob,
    TrendData,
    get_db,
)
from ..scraper import TrendsExtractor, TrendsScheduler, get_scheduler
from .schemas import (
    ExtractionJobResponse,
    ExtractionRequest,
    HealthResponse,
    JobSummaryResponse,
    KeywordStatsResponse,
    PaginatedResponse,
    RegionStatsResponse,
    RelatedQueryResponse,
    RelatedTopicResponse,
    SchedulerStatus,
    TrendDataResponse,
)

# Routers
health_router = APIRouter(prefix="/health", tags=["Health"])
trends_router = APIRouter(prefix="/trends", tags=["Trends Data"])
jobs_router = APIRouter(prefix="/jobs", tags=["Scrape Jobs"])
scheduler_router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


# ===== Health Routes =====

@health_router.get("", response_model=HealthResponse)
async def health_check():
    """Check API health status."""
    return HealthResponse(
        status="healthy",
        version=__version__,
        timestamp=datetime.utcnow(),
    )


# ===== Scheduler Routes =====

@scheduler_router.get("/status", response_model=SchedulerStatus)
async def get_scheduler_status():
    """Get scheduler status."""
    scheduler = get_scheduler()
    return scheduler.get_status()


@scheduler_router.post("/start")
async def start_scheduler():
    """Start the scheduler."""
    scheduler = get_scheduler()
    scheduler.start(run_immediately=False)
    return {"message": "Scheduler started", "status": scheduler.get_status()}


@scheduler_router.post("/stop")
async def stop_scheduler():
    """Stop the scheduler."""
    scheduler = get_scheduler()
    scheduler.stop()
    return {"message": "Scheduler stopped"}


@scheduler_router.post("/trigger")
async def trigger_extraction():
    """Manually trigger extraction."""
    scheduler = get_scheduler()
    scheduler.trigger_now()
    return {"message": "Extraction triggered"}


# ===== Jobs Routes =====

@jobs_router.get("", response_model=list[JobSummaryResponse])
async def list_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List all scrape jobs."""
    jobs = (
        db.query(ScrapeJob)
        .order_by(ScrapeJob.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return jobs


@jobs_router.get("/{job_id}", response_model=JobSummaryResponse)
async def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get a specific job by ID."""
    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@jobs_router.post("/extract", response_model=ExtractionJobResponse)
async def run_extraction(
    request: ExtractionRequest,
    db: Session = Depends(get_db),
):
    """Run a new extraction job."""
    extractor = TrendsExtractor()

    # Convert region codes to full region dicts if provided
    regions = None
    if request.regions:
        regions = [
            {"code": code, "name": code}  # Simple mapping
            for code in request.regions
        ]

    result = extractor.run_extraction(
        keywords=request.keywords,
        regions=regions,
        save_to_db=request.save_to_db,
        save_to_csv=request.save_to_csv,
    )
    return ExtractionJobResponse(**result)


# ===== Trends Data Routes =====

@trends_router.get("/config")
async def get_config():
    """Get current scraping configuration."""
    return {
        "keywords": trends_config.keywords,
        "regions": trends_config.regions,
        "timeframe": trends_config.timeframe,
    }


@trends_router.get("/interest-over-time")
async def get_interest_over_time(
    keyword: Optional[str] = None,
    region: Optional[str] = None,
    job_id: Optional[int] = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get interest over time data."""
    query = db.query(TrendData)

    if keyword:
        query = query.filter(TrendData.keyword == keyword)
    if region:
        query = query.filter(TrendData.region_code == region)
    if job_id:
        query = query.filter(TrendData.job_id == job_id)

    total = query.count()
    items = (
        query.order_by(TrendData.date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return PaginatedResponse(
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
        items=[
            TrendDataResponse(
                id=item.id,
                keyword=item.keyword,
                region_code=item.region_code,
                region_name=item.region_name,
                date=item.date,
                interest=item.interest,
                is_partial=bool(item.is_partial),
            )
            for item in items
        ],
    )


@trends_router.get("/related-queries")
async def get_related_queries(
    keyword: Optional[str] = None,
    region: Optional[str] = None,
    query_type: Optional[str] = Query(default=None, pattern="^(top|rising)$"),
    job_id: Optional[int] = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get related queries data."""
    query = db.query(RelatedQuery)

    if keyword:
        query = query.filter(RelatedQuery.keyword == keyword)
    if region:
        query = query.filter(RelatedQuery.region_code == region)
    if query_type:
        query = query.filter(RelatedQuery.query_type == query_type)
    if job_id:
        query = query.filter(RelatedQuery.job_id == job_id)

    total = query.count()
    items = (
        query.order_by(RelatedQuery.value.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return PaginatedResponse(
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
        items=[
            RelatedQueryResponse(
                id=item.id,
                keyword=item.keyword,
                region_code=item.region_code,
                query_type=item.query_type,
                query_text=item.query_text,
                value=item.value,
                link=item.link,
            )
            for item in items
        ],
    )


@trends_router.get("/related-topics")
async def get_related_topics(
    keyword: Optional[str] = None,
    region: Optional[str] = None,
    topic_type: Optional[str] = Query(default=None, pattern="^(top|rising)$"),
    job_id: Optional[int] = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get related topics data."""
    query = db.query(RelatedTopic)

    if keyword:
        query = query.filter(RelatedTopic.keyword == keyword)
    if region:
        query = query.filter(RelatedTopic.region_code == region)
    if topic_type:
        query = query.filter(RelatedTopic.topic_type == topic_type)
    if job_id:
        query = query.filter(RelatedTopic.job_id == job_id)

    total = query.count()
    items = (
        query.order_by(RelatedTopic.value.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return PaginatedResponse(
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
        items=[
            RelatedTopicResponse(
                id=item.id,
                keyword=item.keyword,
                region_code=item.region_code,
                topic_type=item.topic_type,
                topic_title=item.topic_title,
                topic_mid=item.topic_mid,
                topic_category=item.topic_category,
                value=item.value,
                link=item.link,
            )
            for item in items
        ],
    )


@trends_router.get("/stats/keywords", response_model=list[KeywordStatsResponse])
async def get_keyword_stats(db: Session = Depends(get_db)):
    """Get statistics for all tracked keywords."""
    stats = []
    keywords = db.query(TrendData.keyword).distinct().all()

    for (keyword,) in keywords:
        data_count = db.query(TrendData).filter(TrendData.keyword == keyword).count()
        regions = (
            db.query(TrendData.region_code)
            .filter(TrendData.keyword == keyword)
            .distinct()
            .count()
        )
        latest = (
            db.query(func.max(TrendData.created_at))
            .filter(TrendData.keyword == keyword)
            .scalar()
        )
        avg_interest = (
            db.query(func.avg(TrendData.interest))
            .filter(TrendData.keyword == keyword)
            .scalar()
        )

        stats.append(
            KeywordStatsResponse(
                keyword=keyword,
                total_data_points=data_count,
                regions_covered=regions,
                latest_extraction=latest,
                avg_interest=round(avg_interest, 2) if avg_interest else None,
            )
        )

    return stats


@trends_router.get("/stats/regions", response_model=list[RegionStatsResponse])
async def get_region_stats(db: Session = Depends(get_db)):
    """Get statistics for all tracked regions."""
    stats = []
    regions = (
        db.query(TrendData.region_code, TrendData.region_name)
        .distinct()
        .all()
    )

    for region_code, region_name in regions:
        data_count = (
            db.query(TrendData)
            .filter(TrendData.region_code == region_code)
            .count()
        )
        keywords = (
            db.query(TrendData.keyword)
            .filter(TrendData.region_code == region_code)
            .distinct()
            .count()
        )
        latest = (
            db.query(func.max(TrendData.created_at))
            .filter(TrendData.region_code == region_code)
            .scalar()
        )

        stats.append(
            RegionStatsResponse(
                region_code=region_code,
                region_name=region_name,
                keywords_tracked=keywords,
                total_data_points=data_count,
                latest_extraction=latest,
            )
        )

    return stats

