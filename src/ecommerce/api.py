"""API routes for E-Commerce Analyzer."""

from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Query
from pydantic import BaseModel, Field
from loguru import logger

from .scraper import EcommerceScraper
from .analyzer import ProductAnalyzer
from .config import PLATFORMS, APPAREL_CATEGORIES


router = APIRouter(prefix="/ecommerce", tags=["ecommerce"])


# Pydantic models
class ScrapeRequest(BaseModel):
    """Request for scraping products."""
    platform: str = Field(default="amazon_us", description="Platform to scrape")
    categories: Optional[List[str]] = Field(default=None, description="Categories to scrape")
    max_per_category: int = Field(default=30, ge=1, le=100)


class GenerateSampleRequest(BaseModel):
    """Request for generating sample data."""
    categories: Optional[List[str]] = Field(default=None)
    products_per_category: int = Field(default=20, ge=5, le=50)


# Background tasks
def background_scrape(platform: str, categories: List[str], max_per: int):
    """Background scraping task."""
    scraper = EcommerceScraper()
    try:
        scraper.scrape_all_categories(platform, categories, max_per)
    finally:
        scraper.close()


# API Endpoints
@router.get("/platforms")
async def get_platforms():
    """Get list of supported e-commerce platforms."""
    return {
        "platforms": [
            {"id": k, **v}
            for k, v in PLATFORMS.items()
        ]
    }


@router.get("/categories")
async def get_categories():
    """Get list of women's apparel categories."""
    return {"categories": APPAREL_CATEGORIES}


@router.post("/scrape")
async def scrape_products(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start scraping products from an e-commerce platform.
    
    Note: Real scraping requires proper handling of anti-bot measures.
    Use /sample/generate for demo data.
    """
    logger.info(f"Scrape requested: {request.platform}")
    
    categories = request.categories or [c["id"] for c in APPAREL_CATEGORIES[:5]]
    
    background_tasks.add_task(
        background_scrape,
        request.platform,
        categories,
        request.max_per_category,
    )
    
    return {
        "message": "Scraping started in background",
        "platform": request.platform,
        "categories": categories,
    }


@router.post("/sample/generate")
async def generate_sample_data(request: GenerateSampleRequest):
    """
    Generate sample product data for demo/testing.
    
    This creates realistic sample data without actual web scraping.
    """
    scraper = EcommerceScraper()
    
    try:
        products = scraper.generate_sample_data(
            categories=request.categories,
            products_per_category=request.products_per_category,
        )
        stats = scraper.save_products(products)
        
        return {
            "message": "Sample data generated",
            "products_generated": len(products),
            **stats,
        }
    finally:
        scraper.close()


@router.get("/stats")
async def get_overview_stats():
    """Get overall statistics for all products."""
    analyzer = ProductAnalyzer()
    return analyzer.get_overview_stats()


@router.get("/category/{category_id}")
async def get_category_analysis(
    category_id: str,
    platform: Optional[str] = Query(None, description="Filter by platform"),
):
    """Get detailed analysis for a specific category."""
    analyzer = ProductAnalyzer()
    return analyzer.get_category_analysis(category_id, platform)


@router.get("/platforms/compare")
async def compare_platforms(
    category: Optional[str] = Query(None, description="Filter by category"),
):
    """Compare metrics across platforms."""
    analyzer = ProductAnalyzer()
    return analyzer.get_platform_comparison(category)


@router.get("/brands")
async def get_brand_analysis(
    category: Optional[str] = Query(None, description="Filter by category"),
    top_n: int = Query(default=20, ge=5, le=50),
):
    """Analyze brands across products."""
    analyzer = ProductAnalyzer()
    return analyzer.get_brand_analysis(category, top_n)


@router.get("/products/top")
async def get_top_products(
    category: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    sort_by: str = Query(default="rating", description="rating, reviews, price_low, price_high, discount"),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Get top products by various criteria."""
    analyzer = ProductAnalyzer()
    return {
        "sort_by": sort_by,
        "products": analyzer.get_top_products(category, platform, sort_by, limit),
    }


@router.get("/trends/price")
async def get_price_trends(
    category: Optional[str] = Query(None),
    days: int = Query(default=30, ge=7, le=90),
):
    """Get price trends over time."""
    analyzer = ProductAnalyzer()
    return analyzer.get_price_trends(category, days)


@router.post("/report/generate")
async def generate_category_report(
    category: str = Query(..., description="Category ID"),
    platform: Optional[str] = Query(None),
):
    """Generate and save category statistics report."""
    analyzer = ProductAnalyzer()
    report = analyzer.generate_category_report(category, platform)
    
    if report:
        return {
            "message": "Report generated",
            "report_id": report.id,
            "category": category,
            "platform": platform or "all",
        }
    else:
        return {"error": "Failed to generate report"}
