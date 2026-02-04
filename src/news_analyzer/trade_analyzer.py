"""Trade tension and effectiveness analyzer."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

import pandas as pd
from loguru import logger
from sqlalchemy import func, and_

from .models import (
    NewsArticle,
    NewsAnalysis,
    NewsEntity,
    TradeTensionReport,
    TradeRelation,
)
from .config import ANALYSIS_REGIONS
from ..models import SessionLocal


class TradeAnalyzer:
    """Analyzer for trade tensions and effectiveness based on news."""

    def __init__(self):
        """Initialize the trade analyzer."""
        self.region_map = {r["code"]: r["name"] for r in ANALYSIS_REGIONS}

    def get_analysis_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get summary statistics for analyzed articles.

        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            region: Filter by region code

        Returns:
            Dictionary with summary statistics
        """
        db = SessionLocal()

        try:
            # Base query
            query = db.query(NewsAnalysis).join(NewsArticle)

            # Apply date filters
            if start_date:
                query = query.filter(NewsArticle.published_at >= start_date)
            if end_date:
                query = query.filter(NewsArticle.published_at <= end_date)
            if region:
                query = query.filter(NewsAnalysis.primary_region == region)

            analyses = query.all()

            if not analyses:
                return {"error": "No analyzed articles found"}

            # Calculate statistics
            sentiments = Counter(a.sentiment for a in analyses)
            tensions = Counter(a.tension_level for a in analyses)
            effectiveness = Counter(a.effectiveness_direction for a in analyses)
            regions = Counter(a.primary_region for a in analyses if a.primary_region)

            # Average scores
            avg_sentiment = sum(a.sentiment_score or 0 for a in analyses) / len(analyses)
            avg_tension = sum(a.tension_score or 0 for a in analyses) / len(analyses)
            avg_effectiveness = sum(a.effectiveness_score or 0 for a in analyses) / len(analyses)

            return {
                "total_articles": len(analyses),
                "date_range": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None,
                },
                "sentiment": {
                    "distribution": dict(sentiments),
                    "average_score": round(avg_sentiment, 3),
                },
                "tension": {
                    "distribution": dict(tensions),
                    "average_score": round(avg_tension, 3),
                },
                "effectiveness": {
                    "distribution": dict(effectiveness),
                    "average_score": round(avg_effectiveness, 3),
                },
                "top_regions": dict(regions.most_common(10)),
            }

        finally:
            db.close()

    def get_region_analysis(
        self,
        region: str,
        days_back: int = 30,
    ) -> Dict[str, Any]:
        """
        Get detailed analysis for a specific region.

        Args:
            region: Region code
            days_back: Number of days to analyze

        Returns:
            Dictionary with region-specific analysis
        """
        db = SessionLocal()
        start_date = datetime.utcnow() - timedelta(days=days_back)

        try:
            # Get analyses for region
            analyses = db.query(NewsAnalysis).join(NewsArticle).filter(
                and_(
                    NewsArticle.published_at >= start_date,
                    NewsAnalysis.regions_mentioned.contains([region])
                )
            ).all()

            if not analyses:
                return {"region": region, "error": "No articles found"}

            # Get associated articles
            article_ids = [a.article_id for a in analyses]
            articles = db.query(NewsArticle).filter(
                NewsArticle.id.in_(article_ids)
            ).all()

            # Timeline analysis (by day)
            daily_stats = defaultdict(lambda: {
                "count": 0, "sentiment_sum": 0, "tension_sum": 0
            })

            for analysis in analyses:
                article = next((a for a in articles if a.id == analysis.article_id), None)
                if article:
                    day = article.published_at.strftime("%Y-%m-%d")
                    daily_stats[day]["count"] += 1
                    daily_stats[day]["sentiment_sum"] += analysis.sentiment_score or 0
                    daily_stats[day]["tension_sum"] += analysis.tension_score or 0

            # Calculate daily averages
            timeline = []
            for day, stats in sorted(daily_stats.items()):
                count = stats["count"]
                timeline.append({
                    "date": day,
                    "article_count": count,
                    "avg_sentiment": round(stats["sentiment_sum"] / count, 3) if count else 0,
                    "avg_tension": round(stats["tension_sum"] / count, 3) if count else 0,
                })

            # Get top entities for this region
            entities = db.query(NewsEntity).filter(
                NewsEntity.article_id.in_(article_ids)
            ).all()

            org_counter = Counter()
            for e in entities:
                if e.entity_type == "ORG":
                    org_counter[e.entity_text] += e.count

            # Get related regions
            related_regions = Counter()
            for a in analyses:
                if a.regions_mentioned:
                    for r in a.regions_mentioned:
                        if r != region:
                            related_regions[r] += 1

            return {
                "region": region,
                "region_name": self.region_map.get(region, region),
                "period_days": days_back,
                "total_articles": len(analyses),
                "sentiment": {
                    "positive": sum(1 for a in analyses if a.sentiment == "positive"),
                    "negative": sum(1 for a in analyses if a.sentiment == "negative"),
                    "neutral": sum(1 for a in analyses if a.sentiment == "neutral"),
                    "average": round(
                        sum(a.sentiment_score or 0 for a in analyses) / len(analyses), 3
                    ),
                },
                "tension": {
                    "high": sum(1 for a in analyses if a.tension_level == "high"),
                    "moderate": sum(1 for a in analyses if a.tension_level == "moderate"),
                    "low": sum(1 for a in analyses if a.tension_level == "low"),
                    "positive": sum(1 for a in analyses if a.tension_level == "positive"),
                    "average": round(
                        sum(a.tension_score or 0 for a in analyses) / len(analyses), 3
                    ),
                },
                "timeline": timeline,
                "top_organizations": dict(org_counter.most_common(10)),
                "related_regions": dict(related_regions.most_common(5)),
            }

        finally:
            db.close()

    def get_bilateral_relations(
        self,
        country_a: str,
        country_b: str,
        days_back: int = 30,
    ) -> Dict[str, Any]:
        """
        Analyze trade relations between two countries.

        Args:
            country_a: First country code
            country_b: Second country code
            days_back: Number of days to analyze

        Returns:
            Dictionary with bilateral analysis
        """
        db = SessionLocal()
        start_date = datetime.utcnow() - timedelta(days=days_back)

        try:
            # Find articles mentioning both countries
            analyses = db.query(NewsAnalysis).join(NewsArticle).filter(
                and_(
                    NewsArticle.published_at >= start_date,
                    NewsAnalysis.regions_mentioned.contains([country_a]),
                    NewsAnalysis.regions_mentioned.contains([country_b]),
                )
            ).all()

            if not analyses:
                return {
                    "countries": [country_a, country_b],
                    "error": "No articles found mentioning both countries"
                }

            # Get articles
            article_ids = [a.article_id for a in analyses]
            articles = db.query(NewsArticle).filter(
                NewsArticle.id.in_(article_ids)
            ).order_by(NewsArticle.published_at.desc()).all()

            # Calculate metrics
            avg_sentiment = sum(a.sentiment_score or 0 for a in analyses) / len(analyses)
            avg_tension = sum(a.tension_score or 0 for a in analyses) / len(analyses)
            avg_effectiveness = sum(a.effectiveness_score or 0 for a in analyses) / len(analyses)

            # Determine overall tension level
            if avg_tension >= 0.6:
                overall_tension = "high"
            elif avg_tension >= 0.3:
                overall_tension = "moderate"
            elif avg_tension >= 0:
                overall_tension = "low"
            else:
                overall_tension = "positive"

            # Get key topics (from keywords)
            all_keywords = []
            for a in analyses:
                if a.keywords_extracted:
                    all_keywords.extend(a.keywords_extracted)
            top_keywords = Counter(all_keywords).most_common(15)

            # Recent headlines
            recent_headlines = [
                {
                    "title": a.title,
                    "source": a.source_name,
                    "date": a.published_at.isoformat(),
                    "url": a.url,
                }
                for a in articles[:10]
            ]

            return {
                "countries": {
                    "a": {"code": country_a, "name": self.region_map.get(country_a, country_a)},
                    "b": {"code": country_b, "name": self.region_map.get(country_b, country_b)},
                },
                "period_days": days_back,
                "metrics": {
                    "article_count": len(analyses),
                    "avg_sentiment": round(avg_sentiment, 3),
                    "avg_tension": round(avg_tension, 3),
                    "avg_effectiveness": round(avg_effectiveness, 3),
                    "overall_tension_level": overall_tension,
                },
                "sentiment_distribution": {
                    "positive": sum(1 for a in analyses if a.sentiment == "positive"),
                    "negative": sum(1 for a in analyses if a.sentiment == "negative"),
                    "neutral": sum(1 for a in analyses if a.sentiment == "neutral"),
                },
                "top_keywords": [{"keyword": k, "count": c} for k, c in top_keywords],
                "recent_headlines": recent_headlines,
            }

        finally:
            db.close()

    def generate_daily_report(
        self,
        report_date: Optional[datetime] = None,
    ) -> List[TradeTensionReport]:
        """
        Generate daily trade tension reports for all regions.

        Args:
            report_date: Date for the report (defaults to today)

        Returns:
            List of generated reports
        """
        db = SessionLocal()
        reports = []

        if not report_date:
            report_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        start_date = report_date
        end_date = report_date + timedelta(days=1)

        try:
            # Generate global report
            global_report = self._generate_region_report(
                db, start_date, end_date, region_code=None
            )
            if global_report:
                reports.append(global_report)

            # Generate per-region reports
            for region in ANALYSIS_REGIONS:
                region_report = self._generate_region_report(
                    db, start_date, end_date, region_code=region["code"]
                )
                if region_report:
                    reports.append(region_report)

            # Commit all reports
            for report in reports:
                db.add(report)
            db.commit()

            logger.info(f"Generated {len(reports)} daily reports for {report_date.date()}")

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            db.rollback()

        finally:
            db.close()

        return reports

    def _generate_region_report(
        self,
        db,
        start_date: datetime,
        end_date: datetime,
        region_code: Optional[str] = None,
    ) -> Optional[TradeTensionReport]:
        """Generate a report for a specific region."""
        # Build query
        query = db.query(NewsAnalysis).join(NewsArticle).filter(
            and_(
                NewsArticle.published_at >= start_date,
                NewsArticle.published_at < end_date,
            )
        )

        if region_code:
            query = query.filter(NewsAnalysis.primary_region == region_code)

        analyses = query.all()

        if not analyses:
            return None

        # Calculate metrics
        sentiments = Counter(a.sentiment for a in analyses)
        tensions = Counter(a.tension_level for a in analyses)

        avg_sentiment = sum(a.sentiment_score or 0 for a in analyses) / len(analyses)
        avg_tension = sum(a.tension_score or 0 for a in analyses) / len(analyses)
        avg_effectiveness = sum(a.effectiveness_score or 0 for a in analyses) / len(analyses)

        # Get top entities
        article_ids = [a.article_id for a in analyses]
        entities = db.query(NewsEntity).filter(
            NewsEntity.article_id.in_(article_ids)
        ).all()

        org_counter = Counter()
        country_counter = Counter()
        for e in entities:
            if e.entity_type == "ORG":
                org_counter[e.entity_text] += e.count
            elif e.entity_type == "GPE":
                country_counter[e.entity_text] += e.count

        # Get top keywords
        all_keywords = []
        for a in analyses:
            if a.keywords_extracted:
                all_keywords.extend(a.keywords_extracted)
        keyword_counter = Counter(all_keywords)

        report = TradeTensionReport(
            report_date=start_date,
            region_code=region_code,
            region_name=self.region_map.get(region_code) if region_code else "Global",
            articles_count=len(analyses),
            avg_sentiment_score=round(avg_sentiment, 4),
            avg_tension_score=round(avg_tension, 4),
            avg_effectiveness_score=round(avg_effectiveness, 4),
            positive_count=sentiments.get("positive", 0),
            negative_count=sentiments.get("negative", 0),
            neutral_count=sentiments.get("neutral", 0),
            high_tension_count=tensions.get("high", 0),
            moderate_tension_count=tensions.get("moderate", 0),
            low_tension_count=tensions.get("low", 0),
            top_organizations=dict(org_counter.most_common(10)),
            top_countries=dict(country_counter.most_common(10)),
            top_keywords=dict(keyword_counter.most_common(20)),
        )

        return report

    def get_tension_trend(
        self,
        region: Optional[str] = None,
        days_back: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get tension trend over time.

        Args:
            region: Optional region filter
            days_back: Number of days to analyze

        Returns:
            List of daily tension data
        """
        db = SessionLocal()
        start_date = datetime.utcnow() - timedelta(days=days_back)

        try:
            query = db.query(
                func.date(NewsArticle.published_at).label("date"),
                func.avg(NewsAnalysis.tension_score).label("avg_tension"),
                func.avg(NewsAnalysis.sentiment_score).label("avg_sentiment"),
                func.count(NewsAnalysis.id).label("count"),
            ).join(NewsArticle).filter(
                NewsArticle.published_at >= start_date
            )

            if region:
                query = query.filter(NewsAnalysis.primary_region == region)

            results = query.group_by(
                func.date(NewsArticle.published_at)
            ).order_by(
                func.date(NewsArticle.published_at)
            ).all()

            return [
                {
                    "date": r.date.isoformat() if hasattr(r.date, 'isoformat') else str(r.date),
                    "avg_tension": round(r.avg_tension or 0, 3),
                    "avg_sentiment": round(r.avg_sentiment or 0, 3),
                    "article_count": r.count,
                }
                for r in results
            ]

        finally:
            db.close()

    def get_top_tension_articles(
        self,
        limit: int = 20,
        days_back: int = 7,
        region: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get articles with highest tension scores.

        Args:
            limit: Number of articles to return
            days_back: Number of days to look back
            region: Optional region filter

        Returns:
            List of high-tension articles
        """
        db = SessionLocal()
        start_date = datetime.utcnow() - timedelta(days=days_back)

        try:
            query = db.query(NewsAnalysis, NewsArticle).join(NewsArticle).filter(
                and_(
                    NewsArticle.published_at >= start_date,
                    NewsAnalysis.tension_score.isnot(None),
                )
            )

            if region:
                query = query.filter(NewsAnalysis.primary_region == region)

            results = query.order_by(
                NewsAnalysis.tension_score.desc()
            ).limit(limit).all()

            return [
                {
                    "title": article.title,
                    "source": article.source_name,
                    "url": article.url,
                    "published_at": article.published_at.isoformat(),
                    "tension_score": round(analysis.tension_score or 0, 3),
                    "tension_level": analysis.tension_level,
                    "sentiment": analysis.sentiment,
                    "primary_region": analysis.primary_region,
                    "regions_mentioned": analysis.regions_mentioned,
                }
                for analysis, article in results
            ]

        finally:
            db.close()
