"""API routes for Tariff News Analyzer."""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from loguru import logger

from .news_scraper import NewsScraper
from .text_analyzer import TextAnalyzer
from .trade_analyzer import TradeAnalyzer
from .llm_analyzer import LLMAnalyzer


router = APIRouter(prefix="/news", tags=["news"])

# Pydantic models for API
class FetchNewsRequest(BaseModel):
    """Request model for fetching news."""
    queries: Optional[List[str]] = Field(default=None, description="Search queries")
    regions: Optional[List[str]] = Field(default=None, description="Region codes")
    days_back: int = Field(default=7, ge=1, le=30, description="Days to look back")


class FetchNewsResponse(BaseModel):
    """Response model for news fetch."""
    message: str
    stats: dict


class AnalysisRequest(BaseModel):
    """Request model for analysis."""
    batch_size: int = Field(default=50, ge=1, le=200)


class RegionAnalysisRequest(BaseModel):
    """Request model for region analysis."""
    region: str
    days_back: int = Field(default=30, ge=1, le=90)


class BilateralRequest(BaseModel):
    """Request model for bilateral analysis."""
    country_a: str
    country_b: str
    days_back: int = Field(default=30, ge=1, le=90)


# Background task functions
def background_fetch_news(queries, regions, days_back):
    """Background task for fetching news."""
    scraper = NewsScraper()
    try:
        scraper.fetch_all_sources(queries=queries, regions=regions, days_back=days_back)
    finally:
        scraper.close()


def background_analyze_articles(batch_size):
    """Background task for analyzing articles."""
    analyzer = TextAnalyzer(use_transformers=False)  # Use TextBlob for faster processing
    analyzer.analyze_unprocessed_articles(batch_size=batch_size)


# API Endpoints
@router.post("/fetch", response_model=FetchNewsResponse)
async def fetch_tariff_news(
    request: FetchNewsRequest,
    background_tasks: BackgroundTasks,
):
    """
    Fetch tariff and trade news from multiple sources.

    This endpoint triggers a background job to scrape news from:
    - NewsAPI.org (if API key configured)
    - GNews (if API key configured)
    - Google News RSS (always available)
    """
    logger.info(f"News fetch requested: queries={request.queries}, regions={request.regions}")

    # Start background task
    background_tasks.add_task(
        background_fetch_news,
        request.queries,
        request.regions,
        request.days_back,
    )

    return FetchNewsResponse(
        message="News fetch started in background",
        stats={"status": "processing", "days_back": request.days_back},
    )


@router.post("/fetch/sync", response_model=FetchNewsResponse)
async def fetch_tariff_news_sync(request: FetchNewsRequest):
    """
    Fetch tariff news synchronously (blocking).

    Use this for smaller fetches or testing.
    """
    scraper = NewsScraper()
    try:
        stats = scraper.fetch_all_sources(
            queries=request.queries,
            regions=request.regions,
            days_back=request.days_back,
        )
        return FetchNewsResponse(
            message="News fetch completed",
            stats=stats,
        )
    finally:
        scraper.close()


@router.post("/analyze")
async def analyze_articles(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
):
    """
    Analyze unprocessed news articles.

    Performs sentiment analysis, entity extraction, and trade tension scoring.
    """
    logger.info(f"Analysis requested: batch_size={request.batch_size}")

    background_tasks.add_task(
        background_analyze_articles,
        request.batch_size,
    )

    return {
        "message": "Analysis started in background",
        "batch_size": request.batch_size,
    }


@router.post("/analyze/sync")
async def analyze_articles_sync(request: AnalysisRequest):
    """
    Analyze articles synchronously (blocking).
    """
    analyzer = TextAnalyzer(use_transformers=False)  # Use TextBlob for faster processing
    stats = analyzer.analyze_unprocessed_articles(batch_size=request.batch_size)
    return {
        "message": "Analysis completed",
        "stats": stats,
    }


@router.get("/summary")
async def get_analysis_summary(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    region: Optional[str] = Query(None, description="Region code"),
):
    """
    Get summary statistics for analyzed articles.
    """
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    analyzer = TradeAnalyzer()
    return analyzer.get_analysis_summary(
        start_date=start_dt,
        end_date=end_dt,
        region=region,
    )


@router.get("/region/{region_code}")
async def get_region_analysis(
    region_code: str,
    days_back: int = Query(default=30, ge=1, le=90),
):
    """
    Get detailed trade tension analysis for a specific region.
    """
    analyzer = TradeAnalyzer()
    return analyzer.get_region_analysis(region=region_code, days_back=days_back)


@router.get("/bilateral")
async def get_bilateral_relations(
    country_a: str = Query(..., description="First country code"),
    country_b: str = Query(..., description="Second country code"),
    days_back: int = Query(default=30, ge=1, le=90),
):
    """
    Analyze trade relations between two countries.
    """
    analyzer = TradeAnalyzer()
    return analyzer.get_bilateral_relations(
        country_a=country_a,
        country_b=country_b,
        days_back=days_back,
    )


@router.get("/tension/trend")
async def get_tension_trend(
    region: Optional[str] = Query(None, description="Region code"),
    days_back: int = Query(default=30, ge=1, le=90),
):
    """
    Get trade tension trend over time.
    """
    analyzer = TradeAnalyzer()
    return {
        "region": region or "global",
        "days_back": days_back,
        "trend": analyzer.get_tension_trend(region=region, days_back=days_back),
    }


@router.get("/tension/top")
async def get_top_tension_articles(
    limit: int = Query(default=20, ge=1, le=100),
    days_back: int = Query(default=7, ge=1, le=30),
    region: Optional[str] = Query(None, description="Region code"),
):
    """
    Get articles with highest trade tension scores.
    """
    analyzer = TradeAnalyzer()
    return {
        "limit": limit,
        "days_back": days_back,
        "region": region,
        "articles": analyzer.get_top_tension_articles(
            limit=limit,
            days_back=days_back,
            region=region,
        ),
    }


@router.post("/report/generate")
async def generate_daily_report(
    date: Optional[str] = Query(None, description="Report date (YYYY-MM-DD)"),
):
    """
    Generate daily trade tension report.
    """
    try:
        report_date = datetime.fromisoformat(date) if date else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    analyzer = TradeAnalyzer()
    reports = analyzer.generate_daily_report(report_date=report_date)

    return {
        "message": f"Generated {len(reports)} reports",
        "reports": [
            {
                "region": r.region_code or "global",
                "articles_count": r.articles_count,
                "avg_tension": r.avg_tension_score,
                "avg_sentiment": r.avg_sentiment_score,
            }
            for r in reports
        ],
    }


@router.get("/regions")
async def get_available_regions():
    """
    Get list of regions available for analysis.
    """
    from .config import ANALYSIS_REGIONS
    return {
        "regions": [
            {"code": r["code"], "name": r["name"]}
            for r in ANALYSIS_REGIONS
        ]
    }


@router.get("/queries")
async def get_available_queries():
    """
    Get list of pre-configured search queries.
    """
    from .config import TARIFF_QUERIES
    return {"queries": TARIFF_QUERIES}


# LLM Analysis Endpoints
class LLMAnalysisRequest(BaseModel):
    """Request model for LLM analysis."""
    batch_size: int = Field(default=50, ge=1, le=100)
    force: bool = Field(default=False, description="Re-generate existing summaries")


def background_llm_analysis(batch_size: int, force: bool):
    """Background task for LLM analysis."""
    analyzer = LLMAnalyzer()
    analyzer.analyze_batch(batch_size=batch_size, force=force)


@router.post("/llm/analyze")
async def generate_llm_summaries(
    request: LLMAnalysisRequest,
    background_tasks: BackgroundTasks,
):
    """
    Generate LLM-powered trade impact summaries for news articles.

    Uses OpenAI, Anthropic, or Ollama (local) to analyze articles
    and generate summaries about apparel/fashion trade impact.

    Set one of these environment variables:
    - OPENAI_API_KEY: Use GPT-4o-mini
    - ANTHROPIC_API_KEY: Use Claude 3 Haiku
    - OLLAMA_URL: Use local Ollama (default: http://localhost:11434)
    """
    logger.info(f"LLM analysis requested: batch_size={request.batch_size}")

    background_tasks.add_task(
        background_llm_analysis,
        request.batch_size,
        request.force,
    )

    return {
        "message": "LLM analysis started in background",
        "batch_size": request.batch_size,
        "force": request.force,
    }


@router.post("/llm/analyze/sync")
async def generate_llm_summaries_sync(request: LLMAnalysisRequest):
    """
    Generate LLM summaries synchronously (blocking).
    """
    analyzer = LLMAnalyzer()
    stats = analyzer.analyze_batch(batch_size=request.batch_size, force=request.force)
    return {
        "message": "LLM analysis completed",
        "stats": stats,
    }


@router.get("/llm/status")
async def get_llm_status():
    """
    Check LLM provider status and configuration.
    """
    import os
    
    providers = {
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "ollama_url": os.getenv("OLLAMA_URL", "http://localhost:11434"),
    }
    
    # Try to detect active provider
    analyzer = LLMAnalyzer()
    active_provider = analyzer._provider
    
    return {
        "active_provider": active_provider,
        "configured_providers": providers,
        "fallback_available": True,  # Rule-based fallback always available
    }
