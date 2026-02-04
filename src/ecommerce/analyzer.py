"""Product data analyzer for e-commerce insights."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import statistics

from loguru import logger
from sqlalchemy import func, and_

from .config import PLATFORMS, APPAREL_CATEGORIES, PRICE_RANGES
from .models import Product, PriceHistory, CategoryStats
from ..models import SessionLocal


class ProductAnalyzer:
    """Analyzer for e-commerce product data."""

    def __init__(self):
        """Initialize the analyzer."""
        self.platforms = PLATFORMS
        self.categories = APPAREL_CATEGORIES
        self.price_ranges = PRICE_RANGES

    def get_overview_stats(self) -> Dict[str, Any]:
        """Get overall statistics across all data."""
        db = SessionLocal()

        try:
            total_products = db.query(Product).count()
            
            # By platform
            platform_counts = db.query(
                Product.platform,
                func.count(Product.id)
            ).group_by(Product.platform).all()

            # By category
            category_counts = db.query(
                Product.category,
                func.count(Product.id)
            ).group_by(Product.category).all()

            # Price stats
            price_stats = db.query(
                func.avg(Product.price),
                func.min(Product.price),
                func.max(Product.price),
            ).filter(Product.price.isnot(None)).first()

            # Rating stats
            rating_stats = db.query(
                func.avg(Product.rating),
                func.count(Product.id).filter(Product.rating >= 4.0),
            ).filter(Product.rating.isnot(None)).first()

            # Discount stats
            discounted_count = db.query(Product).filter(
                Product.discount_percent.isnot(None),
                Product.discount_percent > 0,
            ).count()

            return {
                "total_products": total_products,
                "platforms": {p: c for p, c in platform_counts},
                "categories": {c: n for c, n in category_counts},
                "price": {
                    "average": round(price_stats[0] or 0, 2),
                    "min": round(price_stats[1] or 0, 2),
                    "max": round(price_stats[2] or 0, 2),
                },
                "rating": {
                    "average": round(rating_stats[0] or 0, 2),
                    "high_rated_count": rating_stats[1] or 0,
                },
                "discounts": {
                    "discounted_products": discounted_count,
                    "discount_rate": round(discounted_count / total_products * 100, 1) if total_products else 0,
                },
            }

        finally:
            db.close()

    def get_category_analysis(
        self,
        category: str,
        platform: str = None,
    ) -> Dict[str, Any]:
        """
        Get detailed analysis for a category.

        Args:
            category: Category ID
            platform: Optional platform filter

        Returns:
            Category analysis dictionary
        """
        db = SessionLocal()

        try:
            query = db.query(Product).filter(Product.category == category)
            if platform:
                query = query.filter(Product.platform == platform)

            products = query.all()

            if not products:
                return {"category": category, "error": "No products found"}

            prices = [p.price for p in products if p.price]
            ratings = [p.rating for p in products if p.rating]
            reviews = [p.review_count for p in products if p.review_count]

            # Brand analysis
            brand_counter = Counter(p.brand for p in products if p.brand)
            brand_prices = defaultdict(list)
            for p in products:
                if p.brand and p.price:
                    brand_prices[p.brand].append(p.price)

            top_brands = [
                {
                    "brand": brand,
                    "count": count,
                    "avg_price": round(statistics.mean(brand_prices[brand]), 2) if brand_prices[brand] else 0,
                }
                for brand, count in brand_counter.most_common(10)
            ]

            # Price distribution
            price_dist = {r["id"]: 0 for r in self.price_ranges}
            for price in prices:
                for r in self.price_ranges:
                    if r["min"] <= price < r["max"]:
                        price_dist[r["id"]] += 1
                        break

            # Best value products (high rating, reasonable price)
            best_value = sorted(
                [p for p in products if p.rating and p.price],
                key=lambda x: (x.rating / max(x.price, 1)) * 100,
                reverse=True,
            )[:5]

            return {
                "category": category,
                "category_name": next(
                    (c["name"] for c in self.categories if c["id"] == category),
                    category.title()
                ),
                "platform": platform or "all",
                "total_products": len(products),
                "price_stats": {
                    "average": round(statistics.mean(prices), 2) if prices else 0,
                    "median": round(statistics.median(prices), 2) if prices else 0,
                    "min": round(min(prices), 2) if prices else 0,
                    "max": round(max(prices), 2) if prices else 0,
                    "std_dev": round(statistics.stdev(prices), 2) if len(prices) > 1 else 0,
                },
                "rating_stats": {
                    "average": round(statistics.mean(ratings), 2) if ratings else 0,
                    "high_rated": len([r for r in ratings if r >= 4.0]),
                    "low_rated": len([r for r in ratings if r < 3.0]),
                },
                "review_stats": {
                    "total_reviews": sum(reviews),
                    "average_per_product": round(statistics.mean(reviews), 1) if reviews else 0,
                    "max_reviews": max(reviews) if reviews else 0,
                },
                "discounts": {
                    "discounted_count": len([p for p in products if p.discount_percent]),
                    "avg_discount": round(
                        statistics.mean([p.discount_percent for p in products if p.discount_percent]),
                        1
                    ) if any(p.discount_percent for p in products) else 0,
                },
                "top_brands": top_brands,
                "price_distribution": price_dist,
                "best_value_products": [
                    {
                        "name": p.name[:50],
                        "brand": p.brand,
                        "price": p.price,
                        "rating": p.rating,
                        "review_count": p.review_count,
                        "url": p.url,
                    }
                    for p in best_value
                ],
            }

        finally:
            db.close()

    def get_platform_comparison(self, category: str = None) -> Dict[str, Any]:
        """
        Compare metrics across platforms.

        Args:
            category: Optional category filter

        Returns:
            Platform comparison data
        """
        db = SessionLocal()

        try:
            query = db.query(Product)
            if category:
                query = query.filter(Product.category == category)

            products = query.all()

            # Group by platform
            platform_data = defaultdict(list)
            for p in products:
                platform_data[p.platform].append(p)

            comparison = {}
            for platform, prods in platform_data.items():
                prices = [p.price for p in prods if p.price]
                ratings = [p.rating for p in prods if p.rating]
                discounts = [p.discount_percent for p in prods if p.discount_percent]

                comparison[platform] = {
                    "name": self.platforms.get(platform, {}).get("name", platform),
                    "product_count": len(prods),
                    "avg_price": round(statistics.mean(prices), 2) if prices else 0,
                    "median_price": round(statistics.median(prices), 2) if prices else 0,
                    "avg_rating": round(statistics.mean(ratings), 2) if ratings else 0,
                    "avg_discount": round(statistics.mean(discounts), 1) if discounts else 0,
                    "discounted_rate": round(len(discounts) / len(prods) * 100, 1) if prods else 0,
                    "currency": self.platforms.get(platform, {}).get("currency", "USD"),
                }

            return {
                "category": category or "all",
                "platforms": comparison,
            }

        finally:
            db.close()

    def get_brand_analysis(
        self,
        category: str = None,
        top_n: int = 20,
    ) -> Dict[str, Any]:
        """
        Analyze brands across products.

        Args:
            category: Optional category filter
            top_n: Number of top brands to return

        Returns:
            Brand analysis data
        """
        db = SessionLocal()

        try:
            query = db.query(Product).filter(Product.brand.isnot(None))
            if category:
                query = query.filter(Product.category == category)

            products = query.all()

            # Aggregate by brand
            brand_data = defaultdict(lambda: {
                "products": [],
                "prices": [],
                "ratings": [],
                "reviews": [],
            })

            for p in products:
                if p.brand:
                    brand_data[p.brand]["products"].append(p)
                    if p.price:
                        brand_data[p.brand]["prices"].append(p.price)
                    if p.rating:
                        brand_data[p.brand]["ratings"].append(p.rating)
                    if p.review_count:
                        brand_data[p.brand]["reviews"].append(p.review_count)

            # Calculate brand metrics
            brand_metrics = []
            for brand, data in brand_data.items():
                if len(data["products"]) >= 2:  # At least 2 products
                    brand_metrics.append({
                        "brand": brand,
                        "product_count": len(data["products"]),
                        "avg_price": round(statistics.mean(data["prices"]), 2) if data["prices"] else 0,
                        "price_range": {
                            "min": round(min(data["prices"]), 2) if data["prices"] else 0,
                            "max": round(max(data["prices"]), 2) if data["prices"] else 0,
                        },
                        "avg_rating": round(statistics.mean(data["ratings"]), 2) if data["ratings"] else 0,
                        "total_reviews": sum(data["reviews"]),
                        "categories": list(set(p.category for p in data["products"])),
                    })

            # Sort by product count
            brand_metrics.sort(key=lambda x: x["product_count"], reverse=True)

            return {
                "category": category or "all",
                "total_brands": len(brand_data),
                "top_brands": brand_metrics[:top_n],
                "by_price_segment": self._segment_brands_by_price(brand_metrics),
            }

        finally:
            db.close()

    def _segment_brands_by_price(self, brands: List[Dict]) -> Dict[str, List[str]]:
        """Segment brands into price tiers."""
        segments = {r["id"]: [] for r in self.price_ranges}

        for brand in brands:
            avg_price = brand["avg_price"]
            for r in self.price_ranges:
                if r["min"] <= avg_price < r["max"]:
                    segments[r["id"]].append(brand["brand"])
                    break

        return segments

    def get_price_trends(
        self,
        category: str = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get price trends over time.

        Args:
            category: Optional category filter
            days: Number of days to analyze

        Returns:
            Price trend data
        """
        db = SessionLocal()
        start_date = datetime.utcnow() - timedelta(days=days)

        try:
            # Get price history
            query = db.query(PriceHistory).filter(
                PriceHistory.recorded_at >= start_date
            )

            if category:
                # Join with products to filter by category
                product_ids = db.query(Product.id).filter(
                    Product.category == category
                ).all()
                product_ids = [p.id for p in product_ids]
                query = query.filter(PriceHistory.product_id.in_(product_ids))

            history = query.order_by(PriceHistory.recorded_at).all()

            # Group by date
            daily_prices = defaultdict(list)
            for h in history:
                date_key = h.recorded_at.strftime("%Y-%m-%d")
                daily_prices[date_key].append(h.price)

            trends = [
                {
                    "date": date,
                    "avg_price": round(statistics.mean(prices), 2),
                    "min_price": round(min(prices), 2),
                    "max_price": round(max(prices), 2),
                    "count": len(prices),
                }
                for date, prices in sorted(daily_prices.items())
            ]

            return {
                "category": category or "all",
                "period_days": days,
                "data_points": len(history),
                "trends": trends,
            }

        finally:
            db.close()

    def get_top_products(
        self,
        category: str = None,
        platform: str = None,
        sort_by: str = "rating",
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get top products by various criteria.

        Args:
            category: Optional category filter
            platform: Optional platform filter
            sort_by: Sort criteria (rating, reviews, price_low, price_high, discount)
            limit: Number of products to return

        Returns:
            List of top products
        """
        db = SessionLocal()

        try:
            query = db.query(Product)

            if category:
                query = query.filter(Product.category == category)
            if platform:
                query = query.filter(Product.platform == platform)

            # Apply sorting
            if sort_by == "rating":
                query = query.filter(Product.rating.isnot(None))
                query = query.order_by(Product.rating.desc(), Product.review_count.desc())
            elif sort_by == "reviews":
                query = query.order_by(Product.review_count.desc())
            elif sort_by == "price_low":
                query = query.filter(Product.price.isnot(None))
                query = query.order_by(Product.price.asc())
            elif sort_by == "price_high":
                query = query.filter(Product.price.isnot(None))
                query = query.order_by(Product.price.desc())
            elif sort_by == "discount":
                query = query.filter(Product.discount_percent.isnot(None))
                query = query.order_by(Product.discount_percent.desc())

            products = query.limit(limit).all()

            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "brand": p.brand,
                    "category": p.category,
                    "platform": p.platform,
                    "price": p.price,
                    "original_price": p.original_price,
                    "currency": p.currency,
                    "discount_percent": p.discount_percent,
                    "rating": p.rating,
                    "review_count": p.review_count,
                    "url": p.url,
                    "image_url": p.image_url,
                    "is_bestseller": p.is_bestseller,
                }
                for p in products
            ]

        finally:
            db.close()

    def generate_category_report(
        self,
        category: str,
        platform: str = None,
    ) -> Optional[CategoryStats]:
        """
        Generate and save category statistics report.

        Args:
            category: Category ID
            platform: Optional platform filter

        Returns:
            CategoryStats object or None
        """
        db = SessionLocal()

        try:
            analysis = self.get_category_analysis(category, platform)
            
            if "error" in analysis:
                return None

            brand_analysis = self.get_brand_analysis(category)

            report = CategoryStats(
                platform=platform or "all",
                category=category,
                report_date=datetime.utcnow(),
                total_products=analysis["total_products"],
                products_with_discount=analysis["discounts"]["discounted_count"],
                avg_price=analysis["price_stats"]["average"],
                min_price=analysis["price_stats"]["min"],
                max_price=analysis["price_stats"]["max"],
                median_price=analysis["price_stats"]["median"],
                avg_discount=analysis["discounts"]["avg_discount"],
                avg_rating=analysis["rating_stats"]["average"],
                total_reviews=analysis["review_stats"]["total_reviews"],
                avg_review_count=analysis["review_stats"]["average_per_product"],
                top_brands=analysis["top_brands"],
                price_distribution=analysis["price_distribution"],
            )

            db.add(report)
            db.commit()
            db.refresh(report)

            return report

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            db.rollback()
            return None

        finally:
            db.close()
