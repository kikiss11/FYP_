"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .. import __version__
from ..config import settings
from ..models import init_db
from .routes import health_router, jobs_router, scheduler_router, trends_router
from ..news_analyzer.api import router as news_router
from ..ecommerce.api import router as ecommerce_router
from ..macro_analyzer.api import router as macro_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("🚀 Starting Google Trends Scraper API...")
    init_db()
    logger.success(f"✅ API v{__version__} ready!")
    yield
    # Shutdown
    logger.info("👋 Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Google Trends & Tariff News Analyzer API",
    description="""
## 📊 Google Trends Data Extraction API

Automated extraction and retrieval of Google Trends data including:
- **Interest Over Time** - Weekly search interest trends
- **Interest By Region** - Geographic breakdown
- **Related Queries** - Top and rising related searches
- **Related Topics** - Top and rising related themes

## 📰 Tariff News Analyzer

Automated news scraping and trade analysis:
- **News Scraping** - Multi-source news collection (NewsAPI, GNews, Google News RSS)
- **Sentiment Analysis** - FinBERT-powered financial sentiment
- **Trade Tension Analysis** - Measure trade tensions by region
- **Effectiveness Analysis** - Track trade policy effectiveness
- **Entity Extraction** - Identify key organizations and countries

## 📈 Macroeconomic Trade Analyzer

Analyze how economic factors affect women's apparel trade:
- **Correlation Analysis** - GDP, inflation, demographics vs trade volumes
- **Influence Ranking** - Identify top trade drivers
- **Predictive Modeling** - Forecast trade growth by country/product
- **Scenario Analysis** - What-if economic scenarios
- **LLM Insights** - AI-powered analysis summaries

### Features
- ⏰ Automated weekly scraping via scheduler
- 🌍 Multi-region support (30+ countries)
- 🔍 Configurable keywords
- 📁 CSV export capability
- 🗄️ PostgreSQL/SQLite storage
- 🤖 NLP-powered text analysis
- 📊 ML-powered trade predictions
    """,
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(trends_router)
app.include_router(jobs_router)
app.include_router(scheduler_router)
app.include_router(news_router)
app.include_router(ecommerce_router)
app.include_router(macro_router)


@app.get("/", tags=["Root"])
async def root():
    """API root endpoint."""
    return {
        "name": "Google Trends & Tariff News Analyzer API",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
        "dashboards": {
            "trends": "http://localhost:8501",
            "news": "http://localhost:8502",
            "ecommerce": "http://localhost:8503",
            "macro": "http://localhost:8504",
        },
    }


def start_server():
    """Start the API server."""
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )


if __name__ == "__main__":
    start_server()

