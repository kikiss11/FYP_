"""Database models for Google Trends data."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from .config import settings

Base = declarative_base()


class ScrapeJob(Base):
    """Track scraping job executions."""

    __tablename__ = "scrape_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="running")  # running, completed, failed
    keywords_count = Column(Integer, default=0)
    regions_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # Relationships
    trend_data = relationship("TrendData", back_populates="job")
    related_queries = relationship("RelatedQuery", back_populates="job")
    related_topics = relationship("RelatedTopic", back_populates="job")


class TrendData(Base):
    """Store interest over time data."""

    __tablename__ = "trend_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("scrape_jobs.id"), nullable=False)
    keyword = Column(String(255), nullable=False)
    region_code = Column(String(10), nullable=False)
    region_name = Column(String(100), nullable=False)
    date = Column(DateTime, nullable=False)
    interest = Column(Integer, nullable=False)  # 0-100 scale
    is_partial = Column(Integer, default=0)  # Boolean flag for partial data
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    job = relationship("ScrapeJob", back_populates="trend_data")

    __table_args__ = (
        UniqueConstraint(
            "job_id", "keyword", "region_code", "date", name="uix_trend_data"
        ),
    )


class InterestByRegion(Base):
    """Store interest by sub-region data."""

    __tablename__ = "interest_by_region"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("scrape_jobs.id"), nullable=False)
    keyword = Column(String(255), nullable=False)
    parent_region_code = Column(String(10), nullable=False)
    sub_region = Column(String(255), nullable=False)
    interest = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class RelatedQuery(Base):
    """Store related search queries."""

    __tablename__ = "related_queries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("scrape_jobs.id"), nullable=False)
    keyword = Column(String(255), nullable=False)
    region_code = Column(String(10), nullable=False)
    query_type = Column(String(50), nullable=False)  # 'top' or 'rising'
    query_text = Column(String(500), nullable=False)
    value = Column(Integer, nullable=True)  # Interest value or growth %
    link = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    job = relationship("ScrapeJob", back_populates="related_queries")


class RelatedTopic(Base):
    """Store related topics/themes."""

    __tablename__ = "related_topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("scrape_jobs.id"), nullable=False)
    keyword = Column(String(255), nullable=False)
    region_code = Column(String(10), nullable=False)
    topic_type = Column(String(50), nullable=False)  # 'top' or 'rising'
    topic_title = Column(String(500), nullable=False)
    topic_mid = Column(String(100), nullable=True)  # Google Knowledge Graph ID
    topic_category = Column(String(255), nullable=True)
    value = Column(Integer, nullable=True)
    link = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    job = relationship("ScrapeJob", back_populates="related_topics")


# Database engine and session
engine = create_engine(settings.database_url, echo=settings.debug)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    # Import news analyzer models to register them with Base
    from .news_analyzer.models import (
        NewsArticle,
        NewsAnalysis,
        NewsEntity,
        TradeTensionReport,
        TradeRelation,
    )
    # Import e-commerce models
    from .ecommerce.models import (
        Product,
        PriceHistory,
        EcommerceScrapeJob,
        CategoryStats,
    )
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    init_db()

