"""Database models for Tariff News Analyzer."""

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
    JSON,
    Index,
    Boolean,
)
from sqlalchemy.orm import relationship

from ..models import Base


class NewsArticle(Base):
    """Model for storing news articles."""

    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(100), nullable=False)  # NewsAPI, GNews, RSS, etc.
    source_name = Column(String(200))  # Publisher name
    author = Column(String(200))
    title = Column(String(500), nullable=False)
    description = Column(Text)
    content = Column(Text)
    url = Column(String(1000), unique=True, nullable=False)
    url_to_image = Column(String(1000))
    published_at = Column(DateTime, nullable=False)
    collected_at = Column(DateTime, default=datetime.utcnow)
    language = Column(String(10), default="en")

    # Search context
    search_query = Column(String(200))
    search_region = Column(String(10))

    # Processing status
    is_analyzed = Column(Boolean, default=False)
    analyzed_at = Column(DateTime)

    # Relationships
    analysis = relationship("NewsAnalysis", back_populates="article", uselist=False, cascade="all, delete-orphan")
    entities = relationship("NewsEntity", back_populates="article", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_news_published", "published_at"),
        Index("idx_news_source", "source"),
        Index("idx_news_analyzed", "is_analyzed"),
    )


class NewsAnalysis(Base):
    """Model for storing news analysis results."""

    __tablename__ = "news_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("news_articles.id", ondelete="CASCADE"), unique=True)

    # Sentiment analysis (FinBERT)
    sentiment = Column(String(20))  # positive, negative, neutral
    sentiment_score = Column(Float)  # -1.0 to 1.0
    sentiment_confidence = Column(Float)  # 0.0 to 1.0

    # Trade tension analysis
    tension_level = Column(String(20))  # high, moderate, low, positive
    tension_score = Column(Float)  # 0.0 to 1.0
    tension_keywords = Column(JSON)  # List of matched keywords

    # Trade effectiveness analysis
    effectiveness_direction = Column(String(20))  # positive, negative, neutral
    effectiveness_score = Column(Float)  # -1.0 to 1.0
    effectiveness_keywords = Column(JSON)  # List of matched keywords

    # Region relevance
    primary_region = Column(String(10))  # Main region mentioned
    regions_mentioned = Column(JSON)  # List of all regions
    region_scores = Column(JSON)  # Dict of region -> relevance score

    # Topic analysis
    topics = Column(JSON)  # List of identified topics
    keywords_extracted = Column(JSON)  # Key phrases

    # Summary
    summary = Column(Text)  # AI-generated summary

    analyzed_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    article = relationship("NewsArticle", back_populates="analysis")

    __table_args__ = (
        Index("idx_analysis_sentiment", "sentiment"),
        Index("idx_analysis_tension", "tension_level"),
        Index("idx_analysis_region", "primary_region"),
    )


class NewsEntity(Base):
    """Model for storing named entities extracted from news."""

    __tablename__ = "news_entities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("news_articles.id", ondelete="CASCADE"))

    entity_text = Column(String(500), nullable=False)  # Increased size
    entity_type = Column(String(50), nullable=False)  # ORG, GPE, PERSON, MONEY, etc.
    entity_label = Column(String(200))  # Normalized label - increased size
    count = Column(Integer, default=1)  # Occurrence count

    # Relationship
    article = relationship("NewsArticle", back_populates="entities")

    __table_args__ = (
        Index("idx_entity_type", "entity_type"),
        Index("idx_entity_text", "entity_text"),
    )


class TradeTensionReport(Base):
    """Model for storing aggregated trade tension reports."""

    __tablename__ = "trade_tension_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_date = Column(DateTime, nullable=False)
    region_code = Column(String(10))  # Optional: specific region or global
    region_name = Column(String(100))

    # Aggregated metrics
    articles_count = Column(Integer)
    avg_sentiment_score = Column(Float)
    avg_tension_score = Column(Float)
    avg_effectiveness_score = Column(Float)

    # Sentiment distribution
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)

    # Tension distribution
    high_tension_count = Column(Integer, default=0)
    moderate_tension_count = Column(Integer, default=0)
    low_tension_count = Column(Integer, default=0)

    # Top entities
    top_organizations = Column(JSON)
    top_countries = Column(JSON)
    top_topics = Column(JSON)
    top_keywords = Column(JSON)

    # Trend indicators
    tension_trend = Column(String(20))  # increasing, decreasing, stable
    sentiment_trend = Column(String(20))

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_report_date", "report_date"),
        Index("idx_report_region", "region_code"),
    )


class TradeRelation(Base):
    """Model for tracking trade relations between countries."""

    __tablename__ = "trade_relations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_date = Column(DateTime, nullable=False)

    country_a = Column(String(10), nullable=False)
    country_b = Column(String(10), nullable=False)

    # Relation metrics
    mention_count = Column(Integer, default=0)
    avg_sentiment = Column(Float)
    tension_level = Column(String(20))
    tension_score = Column(Float)

    # Key events/topics
    key_topics = Column(JSON)
    key_events = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_relation_countries", "country_a", "country_b"),
        Index("idx_relation_date", "report_date"),
    )
