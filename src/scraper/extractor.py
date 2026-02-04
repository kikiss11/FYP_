"""Data extraction and storage logic."""

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger
from sqlalchemy.orm import Session

from ..config import settings, trends_config
from ..models import (
    InterestByRegion,
    RelatedQuery,
    RelatedTopic,
    ScrapeJob,
    SessionLocal,
    TrendData,
    init_db,
)
from .trends_client import TrendsClient, TrendsResult, get_trends_client


class TrendsExtractor:
    """Extract and store Google Trends data."""

    def __init__(
        self,
        client: Optional[TrendsClient] = None,
        output_dir: Optional[Path] = None,
    ):
        """
        Initialize the extractor.

        Args:
            client: TrendsClient instance (optional)
            output_dir: Directory for CSV exports
        """
        self.client = client or get_trends_client()
        self.output_dir = output_dir or Path(__file__).parent.parent.parent / "data"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_extraction(
        self,
        keywords: Optional[list[str]] = None,
        regions: Optional[list[dict]] = None,
        save_to_db: bool = True,
        save_to_csv: bool = True,
    ) -> dict:
        """
        Run full data extraction for all keywords and regions.

        Args:
            keywords: List of keywords to scrape
            regions: List of region dicts with 'code' and 'name'
            save_to_db: Whether to save to database
            save_to_csv: Whether to export to CSV

        Returns:
            Summary dict with job statistics
        """
        keywords = keywords or trends_config.keywords
        regions = regions or trends_config.regions

        logger.info("=" * 60)
        logger.info("🚀 Starting Google Trends extraction")
        logger.info(f"   Keywords: {keywords}")
        logger.info(f"   Regions: {[r['code'] for r in regions]}")
        logger.info("=" * 60)

        # Initialize database
        if save_to_db:
            init_db()

        # Create scrape job record
        db: Session = SessionLocal()
        job = ScrapeJob(
            keywords_count=len(keywords),
            regions_count=len(regions),
            status="running",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        all_results: list[TrendsResult] = []
        errors: list[str] = []

        try:
            # Fetch data for each keyword-region combination
            for region in regions:
                for keyword in keywords:
                    logger.info(f"Processing: {keyword} ({region['code']})")
                    result = self.client.fetch_all_data(
                        keyword=keyword,
                        region_code=region["code"],
                        region_name=region["name"],
                    )
                    all_results.append(result)

                    if result.error:
                        errors.append(f"{keyword}/{region['code']}: {result.error}")

                    if save_to_db:
                        self._save_result_to_db(db, job.id, result)

            # Export to CSV
            if save_to_csv:
                self._export_to_csv(all_results, job.id)

            # Update job status
            job.status = "completed" if not errors else "completed_with_errors"
            job.completed_at = datetime.utcnow()
            if errors:
                job.error_message = "\n".join(errors[:10])  # First 10 errors
            db.commit()

            logger.success("=" * 60)
            logger.success("✅ Extraction completed!")
            logger.success(f"   Total combinations: {len(all_results)}")
            logger.success(f"   Errors: {len(errors)}")
            logger.success("=" * 60)

            # Store values before closing session
            job_id = job.id
            job_status = job.status

        except Exception as e:
            job.status = "failed"
            job.completed_at = datetime.utcnow()
            job.error_message = str(e)
            db.commit()
            job_id = job.id
            job_status = job.status
            logger.error(f"Extraction failed: {e}")
            db.close()
            raise

        finally:
            db.close()

        return {
            "job_id": job_id,
            "status": job_status,
            "keywords": keywords,
            "regions": [r["code"] for r in regions],
            "total_combinations": len(all_results),
            "errors": len(errors),
        }

    def _save_result_to_db(
        self,
        db: Session,
        job_id: int,
        result: TrendsResult,
    ):
        """Save a TrendsResult to the database."""
        # Save interest over time
        if result.interest_over_time is not None and not result.interest_over_time.empty:
            df = result.interest_over_time
            for idx, row in df.iterrows():
                is_partial = 1 if "isPartial" in df.columns and row.get("isPartial", False) else 0
                trend_data = TrendData(
                    job_id=job_id,
                    keyword=result.keyword,
                    region_code=result.region_code,
                    region_name=result.region_name,
                    date=idx,
                    interest=row.get(result.keyword, 0),
                    is_partial=is_partial,
                )
                db.add(trend_data)

        # Save interest by region
        if result.interest_by_region is not None and not result.interest_by_region.empty:
            df = result.interest_by_region
            for sub_region, row in df.iterrows():
                interest_data = InterestByRegion(
                    job_id=job_id,
                    keyword=result.keyword,
                    parent_region_code=result.region_code,
                    sub_region=sub_region,
                    interest=row.get(result.keyword, 0),
                )
                db.add(interest_data)

        # Save related queries (top)
        if result.related_queries_top is not None and not result.related_queries_top.empty:
            for _, row in result.related_queries_top.iterrows():
                query = RelatedQuery(
                    job_id=job_id,
                    keyword=result.keyword,
                    region_code=result.region_code,
                    query_type="top",
                    query_text=row.get("query", ""),
                    value=row.get("value", 0),
                    link=row.get("link", ""),
                )
                db.add(query)

        # Save related queries (rising)
        if result.related_queries_rising is not None and not result.related_queries_rising.empty:
            for _, row in result.related_queries_rising.iterrows():
                query = RelatedQuery(
                    job_id=job_id,
                    keyword=result.keyword,
                    region_code=result.region_code,
                    query_type="rising",
                    query_text=row.get("query", ""),
                    value=row.get("value", 0),
                    link=row.get("link", ""),
                )
                db.add(query)

        # Save related topics (top)
        if result.related_topics_top is not None and not result.related_topics_top.empty:
            for _, row in result.related_topics_top.iterrows():
                topic = RelatedTopic(
                    job_id=job_id,
                    keyword=result.keyword,
                    region_code=result.region_code,
                    topic_type="top",
                    topic_title=row.get("topic_title", ""),
                    topic_mid=row.get("topic_mid", ""),
                    topic_category=row.get("topic_type", ""),
                    value=row.get("value", 0),
                    link=row.get("link", ""),
                )
                db.add(topic)

        # Save related topics (rising)
        if result.related_topics_rising is not None and not result.related_topics_rising.empty:
            for _, row in result.related_topics_rising.iterrows():
                topic = RelatedTopic(
                    job_id=job_id,
                    keyword=result.keyword,
                    region_code=result.region_code,
                    topic_type="rising",
                    topic_title=row.get("topic_title", ""),
                    topic_mid=row.get("topic_mid", ""),
                    topic_category=row.get("topic_type", ""),
                    value=row.get("value", 0),
                    link=row.get("link", ""),
                )
                db.add(topic)

        db.commit()
        logger.debug(f"Saved data for {result.keyword} ({result.region_code})")

    def _export_to_csv(self, results: list[TrendsResult], job_id: int):
        """Export results to CSV files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_dir = self.output_dir / f"job_{job_id}_{timestamp}"
        job_dir.mkdir(parents=True, exist_ok=True)

        # Interest over time
        iot_data = []
        for r in results:
            if r.interest_over_time is not None and not r.interest_over_time.empty:
                df = r.interest_over_time.copy()
                df["keyword"] = r.keyword
                df["region_code"] = r.region_code
                df["region_name"] = r.region_name
                df["date"] = df.index
                iot_data.append(df)

        if iot_data:
            combined = pd.concat(iot_data, ignore_index=True)
            combined.to_csv(job_dir / "interest_over_time.csv", index=False)
            logger.info(f"Exported interest_over_time.csv ({len(combined)} rows)")

        # Related queries
        queries_data = []
        for r in results:
            for qtype, df in [
                ("top", r.related_queries_top),
                ("rising", r.related_queries_rising),
            ]:
                if df is not None and not df.empty:
                    df = df.copy()
                    df["keyword"] = r.keyword
                    df["region_code"] = r.region_code
                    df["query_type"] = qtype
                    queries_data.append(df)

        if queries_data:
            combined = pd.concat(queries_data, ignore_index=True)
            combined.to_csv(job_dir / "related_queries.csv", index=False)
            logger.info(f"Exported related_queries.csv ({len(combined)} rows)")

        # Related topics
        topics_data = []
        for r in results:
            for ttype, df in [
                ("top", r.related_topics_top),
                ("rising", r.related_topics_rising),
            ]:
                if df is not None and not df.empty:
                    df = df.copy()
                    df["keyword"] = r.keyword
                    df["region_code"] = r.region_code
                    df["topic_type"] = ttype
                    topics_data.append(df)

        if topics_data:
            combined = pd.concat(topics_data, ignore_index=True)
            combined.to_csv(job_dir / "related_topics.csv", index=False)
            logger.info(f"Exported related_topics.csv ({len(combined)} rows)")

        logger.success(f"CSV exports saved to: {job_dir}")


def run_manual_extraction():
    """Run extraction manually (for testing or CLI)."""
    extractor = TrendsExtractor()
    return extractor.run_extraction()


if __name__ == "__main__":
    # Run extraction when called directly
    result = run_manual_extraction()
    print(f"\n📊 Extraction Summary: {result}")

