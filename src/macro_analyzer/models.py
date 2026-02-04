"""Database models for Macroeconomic Trade Analyzer."""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, Boolean, 
    Text, ForeignKey, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class MacroIndicator(Base):
    """Store macroeconomic indicators by country and time period."""
    __tablename__ = "macro_indicators"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    country_code = Column(String(10), nullable=False, index=True)
    country_name = Column(String(100))
    indicator_code = Column(String(50), nullable=False, index=True)
    indicator_name = Column(String(200))
    
    # Time period
    year = Column(Integer, nullable=False, index=True)
    quarter = Column(Integer, nullable=True)  # 1-4, null for annual
    month = Column(Integer, nullable=True)    # 1-12, null for quarterly/annual
    period_date = Column(Date, nullable=False)
    
    # Values
    value = Column(Float)
    value_unit = Column(String(50))
    yoy_change = Column(Float)  # Year-over-year change
    qoq_change = Column(Float)  # Quarter-over-quarter change
    
    # Metadata
    source = Column(String(100))
    source_url = Column(String(500))
    collected_at = Column(DateTime, default=datetime.utcnow)
    is_estimate = Column(Boolean, default=False)
    notes = Column(Text)
    
    __table_args__ = (
        UniqueConstraint('country_code', 'indicator_code', 'year', 'quarter', 'month', 
                        name='uix_macro_indicator'),
        Index('idx_macro_country_year', 'country_code', 'year'),
    )


class ApparelTradeData(Base):
    """Store apparel trade data (imports/exports) by country and product."""
    __tablename__ = "apparel_trade_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Country information
    reporter_code = Column(String(10), nullable=False, index=True)
    reporter_name = Column(String(100))
    partner_code = Column(String(10), index=True)  # Trade partner, 'WLD' for world total
    partner_name = Column(String(100))
    
    # Product information
    hs_code = Column(String(10), nullable=False, index=True)
    product_name = Column(String(200))
    product_category = Column(String(50))  # formal, casual, underwear, etc.
    
    # Trade flow
    trade_flow = Column(String(20), nullable=False)  # 'import' or 'export'
    
    # Time period
    year = Column(Integer, nullable=False, index=True)
    quarter = Column(Integer, nullable=True)
    month = Column(Integer, nullable=True)
    period_date = Column(Date, nullable=False)
    
    # Trade values
    trade_value_usd = Column(Float)  # Value in USD
    trade_quantity = Column(Float)    # Quantity (if available)
    quantity_unit = Column(String(50))  # kg, pieces, etc.
    unit_price = Column(Float)  # Price per unit
    
    # Growth metrics
    yoy_growth = Column(Float)  # Year-over-year growth %
    market_share = Column(Float)  # Share of total market %
    
    # Metadata
    source = Column(String(100))
    collected_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('reporter_code', 'partner_code', 'hs_code', 'trade_flow', 
                        'year', 'quarter', 'month', name='uix_trade_data'),
        Index('idx_trade_reporter_year', 'reporter_code', 'year'),
        Index('idx_trade_hs_year', 'hs_code', 'year'),
    )


class DemographicData(Base):
    """Store demographic data with focus on female population."""
    __tablename__ = "demographic_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    country_code = Column(String(10), nullable=False, index=True)
    country_name = Column(String(100))
    year = Column(Integer, nullable=False, index=True)
    
    # Total population
    total_population = Column(Float)  # in millions
    male_population = Column(Float)
    female_population = Column(Float)
    female_ratio = Column(Float)  # percentage
    
    # Age groups (female)
    female_0_14 = Column(Float)   # Youth
    female_15_24 = Column(Float)  # Young adults
    female_25_54 = Column(Float)  # Prime working age
    female_55_64 = Column(Float)  # Pre-retirement
    female_65_plus = Column(Float)  # Retirement
    
    # Working age female (key for apparel consumption)
    working_age_female = Column(Float)  # 15-64 total
    working_age_female_ratio = Column(Float)
    
    # Urban/Rural
    urbanization_rate = Column(Float)
    urban_female_population = Column(Float)
    
    # Other demographics
    median_age = Column(Float)
    female_labor_participation = Column(Float)
    
    # Metadata
    source = Column(String(100))
    collected_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('country_code', 'year', name='uix_demographic'),
    )


class MacroTradeCorrelation(Base):
    """Store correlation analysis between macro indicators and trade."""
    __tablename__ = "macro_trade_correlations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Analysis scope
    country_code = Column(String(10), index=True)  # null for global
    hs_code = Column(String(10), index=True)  # null for all apparel
    trade_flow = Column(String(20))  # import, export, or both
    
    # Indicator being analyzed
    indicator_code = Column(String(50), nullable=False)
    indicator_name = Column(String(200))
    
    # Correlation results
    correlation_coefficient = Column(Float)  # Pearson correlation
    p_value = Column(Float)  # Statistical significance
    r_squared = Column(Float)  # Coefficient of determination
    
    # Time lag analysis
    optimal_lag_months = Column(Integer)  # Lag for best correlation
    lagged_correlation = Column(Float)
    
    # Impact direction
    impact_direction = Column(String(20))  # positive, negative, neutral
    elasticity = Column(Float)  # % change in trade per 1% change in indicator
    
    # Analysis period
    analysis_start_date = Column(Date)
    analysis_end_date = Column(Date)
    data_points = Column(Integer)
    
    # Metadata
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    
    __table_args__ = (
        Index('idx_correlation_indicator', 'indicator_code'),
    )


class TradePrediction(Base):
    """Store trade predictions based on macro indicators."""
    __tablename__ = "trade_predictions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Prediction scope
    country_code = Column(String(10), nullable=False, index=True)
    hs_code = Column(String(10), index=True)  # null for total apparel
    trade_flow = Column(String(20), nullable=False)  # import or export
    
    # Prediction period
    prediction_date = Column(Date, nullable=False)
    prediction_period = Column(String(20))  # monthly, quarterly, yearly
    
    # Predicted values
    predicted_value = Column(Float)  # Predicted trade value in USD
    predicted_growth = Column(Float)  # Predicted YoY growth %
    
    # Confidence
    confidence_lower = Column(Float)  # Lower bound (95% CI)
    confidence_upper = Column(Float)  # Upper bound (95% CI)
    prediction_confidence = Column(Float)  # 0-1 confidence score
    
    # Model info
    model_type = Column(String(50))  # linear, xgboost, lstm, etc.
    model_version = Column(String(20))
    features_used = Column(JSON)  # List of indicators used
    feature_importance = Column(JSON)  # Importance scores
    
    # Actual values (filled in when available)
    actual_value = Column(Float, nullable=True)
    prediction_error = Column(Float, nullable=True)
    mape = Column(Float, nullable=True)  # Mean Absolute Percentage Error
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('country_code', 'hs_code', 'trade_flow', 'prediction_date', 
                        'model_type', name='uix_prediction'),
    )


class MacroAnalysisReport(Base):
    """Store generated analysis reports."""
    __tablename__ = "macro_analysis_reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Report scope
    report_type = Column(String(50))  # country, product, global, correlation
    country_code = Column(String(10), index=True)
    hs_code = Column(String(10), index=True)
    
    # Report content
    title = Column(String(200))
    summary = Column(Text)
    key_findings = Column(JSON)  # List of key findings
    recommendations = Column(JSON)  # List of recommendations
    full_report = Column(Text)  # Full markdown/HTML report
    
    # Charts/visualizations (JSON paths or base64)
    visualizations = Column(JSON)
    
    # Analysis period
    analysis_start = Column(Date)
    analysis_end = Column(Date)
    
    # LLM generated content
    llm_analysis = Column(Text)
    llm_model = Column(String(50))
    
    # Metadata
    generated_at = Column(DateTime, default=datetime.utcnow)


class InfluenceFactor(Base):
    """Store influence factor rankings for trade predictions."""
    __tablename__ = "influence_factors"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Scope
    country_code = Column(String(10), index=True)  # null for global
    hs_code = Column(String(10), index=True)
    trade_flow = Column(String(20))
    
    # Factor details
    indicator_code = Column(String(50), nullable=False)
    indicator_name = Column(String(200))
    
    # Ranking
    influence_rank = Column(Integer)  # 1 = most influential
    influence_score = Column(Float)  # Normalized 0-100
    
    # Impact details
    correlation = Column(Float)
    elasticity = Column(Float)
    time_lag = Column(Integer)  # months
    
    # Direction and magnitude
    impact_direction = Column(String(20))  # positive, negative
    impact_magnitude = Column(String(20))  # high, medium, low
    
    # Statistical confidence
    confidence_level = Column(Float)  # 0-1
    
    # Explanation
    explanation = Column(Text)
    
    # Metadata
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_influence_rank', 'country_code', 'trade_flow', 'influence_rank'),
    )
