"""Database models for E-Commerce product data."""

from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    JSON,
    Index,
    Boolean,
)

from ..models import Base


class Product(Base):
    """Model for storing product information."""

    __tablename__ = "ecommerce_products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Platform info
    platform = Column(String(50), nullable=False)  # amazon_us, hktv_mall, etc.
    platform_product_id = Column(String(200))  # ASIN, SKU, etc.
    
    # Product details
    name = Column(String(500), nullable=False)
    brand = Column(String(200))
    category = Column(String(100))  # dresses, tops, pants, etc.
    subcategory = Column(String(100))
    
    # Pricing
    price = Column(Float)
    original_price = Column(Float)  # Before discount
    currency = Column(String(10), default="USD")
    discount_percent = Column(Float)
    
    # Reviews
    rating = Column(Float)  # 0-5 scale
    review_count = Column(Integer, default=0)
    
    # Product attributes
    colors = Column(JSON)  # List of available colors
    sizes = Column(JSON)  # List of available sizes
    materials = Column(JSON)  # List of materials
    
    # URLs
    url = Column(String(1000))
    image_url = Column(String(1000))
    
    # Metadata
    is_bestseller = Column(Boolean, default=False)
    is_prime = Column(Boolean, default=False)  # Amazon Prime
    seller = Column(String(200))
    
    # Timestamps
    scraped_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_product_platform", "platform"),
        Index("idx_product_category", "category"),
        Index("idx_product_brand", "brand"),
        Index("idx_product_price", "price"),
        Index("idx_product_rating", "rating"),
    )


class PriceHistory(Base):
    """Model for tracking price changes over time."""

    __tablename__ = "ecommerce_price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, nullable=False)
    
    price = Column(Float, nullable=False)
    original_price = Column(Float)
    currency = Column(String(10))
    
    recorded_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_price_history_product", "product_id"),
        Index("idx_price_history_date", "recorded_at"),
    )


class EcommerceScrapeJob(Base):
    """Model for tracking scrape jobs."""

    __tablename__ = "ecommerce_scrape_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    platform = Column(String(50), nullable=False)
    category = Column(String(100))
    
    status = Column(String(50), default="running")  # running, completed, failed
    products_found = Column(Integer, default=0)
    products_saved = Column(Integer, default=0)
    error_message = Column(Text)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    __table_args__ = (
        Index("idx_scrape_job_platform", "platform"),
        Index("idx_scrape_job_status", "status"),
    )


class CategoryStats(Base):
    """Model for storing aggregated category statistics."""

    __tablename__ = "ecommerce_category_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    platform = Column(String(50), nullable=False)
    category = Column(String(100), nullable=False)
    report_date = Column(DateTime, nullable=False)
    
    # Product counts
    total_products = Column(Integer, default=0)
    products_with_discount = Column(Integer, default=0)
    bestseller_count = Column(Integer, default=0)
    
    # Price stats
    avg_price = Column(Float)
    min_price = Column(Float)
    max_price = Column(Float)
    median_price = Column(Float)
    
    # Discount stats
    avg_discount = Column(Float)
    max_discount = Column(Float)
    
    # Review stats
    avg_rating = Column(Float)
    total_reviews = Column(Integer)
    avg_review_count = Column(Float)
    
    # Top brands
    top_brands = Column(JSON)  # List of {brand, count, avg_price}
    
    # Price distribution
    price_distribution = Column(JSON)  # {budget: 10, affordable: 20, ...}
    
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_category_stats_platform", "platform"),
        Index("idx_category_stats_category", "category"),
        Index("idx_category_stats_date", "report_date"),
    )
