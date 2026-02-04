"""E-Commerce web scraper for women's apparel products."""

import re
import time
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, quote_plus

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from .config import (
    PLATFORMS,
    APPAREL_CATEGORIES,
    SCRAPE_DELAY,
    MAX_PRODUCTS_PER_CATEGORY,
    REQUEST_TIMEOUT,
)
from .models import Product, PriceHistory, EcommerceScrapeJob
from ..models import SessionLocal


class EcommerceScraper:
    """Multi-platform e-commerce scraper."""

    def __init__(self):
        """Initialize the scraper."""
        self.client = httpx.Client(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
            }
        )
        self.delay = SCRAPE_DELAY

    def _random_delay(self):
        """Add random delay to avoid detection."""
        delay = self.delay + random.uniform(0.5, 2.0)
        time.sleep(delay)

    def _clean_price(self, price_str: str) -> Optional[float]:
        """Extract numeric price from string."""
        if not price_str:
            return None
        # Remove currency symbols and commas
        cleaned = re.sub(r'[^\d.]', '', price_str)
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _clean_rating(self, rating_str: str) -> Optional[float]:
        """Extract numeric rating from string."""
        if not rating_str:
            return None
        match = re.search(r'(\d+\.?\d*)', rating_str)
        if match:
            return float(match.group(1))
        return None

    def _clean_review_count(self, count_str: str) -> int:
        """Extract review count from string."""
        if not count_str:
            return 0
        # Handle formats like "1,234" or "1.2K"
        cleaned = count_str.replace(',', '').replace(' ', '')
        if 'K' in cleaned.upper():
            match = re.search(r'(\d+\.?\d*)', cleaned)
            if match:
                return int(float(match.group(1)) * 1000)
        match = re.search(r'(\d+)', cleaned)
        if match:
            return int(match.group(1))
        return 0

    def scrape_amazon(
        self,
        category: str,
        region: str = "us",
        max_products: int = MAX_PRODUCTS_PER_CATEGORY,
    ) -> List[Dict[str, Any]]:
        """
        Scrape products from Amazon.

        Args:
            category: Category to scrape (dresses, tops, etc.)
            region: Amazon region (us, uk, jp)
            max_products: Maximum products to fetch

        Returns:
            List of product dictionaries
        """
        platform_key = f"amazon_{region}"
        platform = PLATFORMS.get(platform_key)
        if not platform:
            logger.error(f"Unknown platform: {platform_key}")
            return []

        products = []
        base_url = platform["base_url"]
        
        # Find category config
        cat_config = next(
            (c for c in APPAREL_CATEGORIES if c["id"] == category),
            None
        )
        if not cat_config:
            logger.error(f"Unknown category: {category}")
            return []

        search_term = f"women {cat_config['name']}"
        search_url = f"{base_url}/s?k={quote_plus(search_term)}&rh=n:7141123011"
        
        logger.info(f"Scraping Amazon {region.upper()}: {search_term}")

        try:
            page = 1
            while len(products) < max_products and page <= 5:
                url = f"{search_url}&page={page}"
                response = self.client.get(url)
                
                if response.status_code != 200:
                    logger.warning(f"Amazon returned {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find product containers
                items = soup.select('[data-component-type="s-search-result"]')
                
                if not items:
                    logger.info("No more products found")
                    break

                for item in items:
                    if len(products) >= max_products:
                        break

                    try:
                        product = self._parse_amazon_product(item, platform_key, category)
                        if product:
                            products.append(product)
                    except Exception as e:
                        logger.debug(f"Error parsing product: {e}")
                        continue

                page += 1
                self._random_delay()

        except Exception as e:
            logger.error(f"Amazon scraping error: {e}")

        logger.info(f"Scraped {len(products)} products from Amazon {region.upper()}")
        return products

    def _parse_amazon_product(
        self,
        item: BeautifulSoup,
        platform: str,
        category: str,
    ) -> Optional[Dict[str, Any]]:
        """Parse a single Amazon product item."""
        # Product name
        name_elem = item.select_one('h2 a span')
        if not name_elem:
            return None
        name = name_elem.get_text(strip=True)

        # ASIN
        asin = item.get('data-asin', '')

        # URL
        link_elem = item.select_one('h2 a')
        url = ""
        if link_elem and link_elem.get('href'):
            url = urljoin(PLATFORMS[platform]["base_url"], link_elem['href'])

        # Price
        price_elem = item.select_one('.a-price .a-offscreen')
        price = self._clean_price(price_elem.get_text() if price_elem else None)

        # Original price (if discounted)
        orig_price_elem = item.select_one('.a-price.a-text-price .a-offscreen')
        original_price = self._clean_price(
            orig_price_elem.get_text() if orig_price_elem else None
        )

        # Rating
        rating_elem = item.select_one('.a-icon-star-small .a-icon-alt')
        rating = self._clean_rating(rating_elem.get_text() if rating_elem else None)

        # Review count
        review_elem = item.select_one('[data-csa-c-func-deps="aui-da-a-popover"] span:last-child')
        if not review_elem:
            review_elem = item.select_one('.a-size-base.s-underline-text')
        review_count = self._clean_review_count(
            review_elem.get_text() if review_elem else None
        )

        # Image
        img_elem = item.select_one('.s-image')
        image_url = img_elem.get('src', '') if img_elem else ''

        # Brand (often in the product name or separate element)
        brand = ""
        brand_elem = item.select_one('.a-size-base-plus.a-color-base')
        if brand_elem:
            brand = brand_elem.get_text(strip=True)

        # Prime badge
        is_prime = bool(item.select_one('.a-icon-prime'))

        # Bestseller badge
        is_bestseller = bool(item.select_one('.a-badge-text'))

        # Calculate discount
        discount = None
        if price and original_price and original_price > price:
            discount = round((1 - price / original_price) * 100, 1)

        return {
            "platform": platform,
            "platform_product_id": asin,
            "name": name,
            "brand": brand,
            "category": category,
            "price": price,
            "original_price": original_price,
            "currency": PLATFORMS[platform]["currency"],
            "discount_percent": discount,
            "rating": rating,
            "review_count": review_count,
            "url": url,
            "image_url": image_url,
            "is_prime": is_prime,
            "is_bestseller": is_bestseller,
            "scraped_at": datetime.utcnow(),
        }

    def scrape_hktv_mall(
        self,
        category: str,
        max_products: int = MAX_PRODUCTS_PER_CATEGORY,
    ) -> List[Dict[str, Any]]:
        """
        Scrape products from HKTV Mall.

        Args:
            category: Category to scrape
            max_products: Maximum products to fetch

        Returns:
            List of product dictionaries
        """
        products = []
        platform = PLATFORMS["hktv_mall"]
        
        cat_config = next(
            (c for c in APPAREL_CATEGORIES if c["id"] == category),
            None
        )
        if not cat_config:
            return []

        # HKTV Mall API endpoint
        search_term = f"女裝 {cat_config['keywords'][0]}"  # Chinese search
        api_url = f"https://www.hktvmall.com/hktv/zh/ajax/search_products"
        
        logger.info(f"Scraping HKTV Mall: {cat_config['name']}")

        try:
            params = {
                "q": search_term,
                "page": 0,
                "size": min(max_products, 48),
                "sort": "RELEVANCE",
            }
            
            response = self.client.get(api_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("products", [])
                
                for item in items[:max_products]:
                    try:
                        product = self._parse_hktv_product(item, category)
                        if product:
                            products.append(product)
                    except Exception as e:
                        logger.debug(f"Error parsing HKTV product: {e}")

        except Exception as e:
            logger.error(f"HKTV Mall scraping error: {e}")

        logger.info(f"Scraped {len(products)} products from HKTV Mall")
        return products

    def _parse_hktv_product(
        self,
        item: Dict,
        category: str,
    ) -> Optional[Dict[str, Any]]:
        """Parse a single HKTV Mall product."""
        return {
            "platform": "hktv_mall",
            "platform_product_id": item.get("code", ""),
            "name": item.get("name", ""),
            "brand": item.get("brandName", ""),
            "category": category,
            "price": item.get("price", {}).get("value"),
            "original_price": item.get("wasPrice", {}).get("value"),
            "currency": "HKD",
            "discount_percent": item.get("discountPercent"),
            "rating": item.get("averageRating"),
            "review_count": item.get("numberOfReviews", 0),
            "url": f"https://www.hktvmall.com{item.get('url', '')}",
            "image_url": item.get("primaryImage", {}).get("url", ""),
            "seller": item.get("storeName", ""),
            "scraped_at": datetime.utcnow(),
        }

    def generate_sample_data(
        self,
        categories: List[str] = None,
        products_per_category: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Generate sample product data for demo/testing.

        Args:
            categories: Categories to generate
            products_per_category: Products per category

        Returns:
            List of sample products
        """
        import random

        if not categories:
            categories = ["dresses", "tops", "pants", "skirts", "jackets"]

        brands = [
            "Zara", "H&M", "Uniqlo", "Gap", "Mango", "Forever 21",
            "Topshop", "ASOS", "Shein", "Fashion Nova", "Boohoo",
            "Missguided", "PrettyLittleThing", "Nike", "Adidas",
        ]

        products = []
        platforms = ["amazon_us", "amazon_uk", "hktv_mall"]

        for category in categories:
            cat_config = next(
                (c for c in APPAREL_CATEGORIES if c["id"] == category),
                {"name": category.title()}
            )

            for i in range(products_per_category):
                platform = random.choice(platforms)
                brand = random.choice(brands)
                
                base_price = random.uniform(15, 150)
                has_discount = random.random() > 0.6
                
                if has_discount:
                    discount = random.uniform(10, 50)
                    original_price = base_price
                    price = round(base_price * (1 - discount / 100), 2)
                else:
                    price = round(base_price, 2)
                    original_price = None
                    discount = None

                products.append({
                    "platform": platform,
                    "platform_product_id": f"SAMPLE-{category[:3].upper()}-{i:04d}",
                    "name": f"{brand} Women's {cat_config['name']} - Style {i+1}",
                    "brand": brand,
                    "category": category,
                    "price": price,
                    "original_price": original_price,
                    "currency": PLATFORMS[platform]["currency"],
                    "discount_percent": round(discount, 1) if discount else None,
                    "rating": round(random.uniform(3.0, 5.0), 1),
                    "review_count": random.randint(5, 5000),
                    "url": f"https://example.com/product/{category}/{i}",
                    "image_url": f"https://picsum.photos/seed/{category}{i}/300/400",
                    "is_bestseller": random.random() > 0.85,
                    "is_prime": platform.startswith("amazon") and random.random() > 0.3,
                    "seller": f"{brand} Official" if random.random() > 0.5 else "Third Party Seller",
                    "colors": random.sample(["Black", "White", "Red", "Blue", "Pink", "Green", "Navy", "Beige"], random.randint(2, 5)),
                    "sizes": ["XS", "S", "M", "L", "XL"][:random.randint(3, 5)],
                    "scraped_at": datetime.utcnow(),
                })

        return products

    def save_products(self, products: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Save products to database.

        Args:
            products: List of product dictionaries

        Returns:
            Statistics dictionary
        """
        db = SessionLocal()
        stats = {"saved": 0, "updated": 0, "failed": 0}

        try:
            for product_data in products:
                try:
                    # Check if product exists
                    existing = db.query(Product).filter(
                        Product.platform == product_data["platform"],
                        Product.platform_product_id == product_data["platform_product_id"],
                    ).first()

                    if existing:
                        # Update existing product
                        for key, value in product_data.items():
                            if key != "scraped_at" and value is not None:
                                setattr(existing, key, value)
                        existing.updated_at = datetime.utcnow()
                        
                        # Record price history if changed
                        if existing.price != product_data.get("price"):
                            history = PriceHistory(
                                product_id=existing.id,
                                price=product_data.get("price"),
                                original_price=product_data.get("original_price"),
                                currency=product_data.get("currency"),
                            )
                            db.add(history)
                        
                        stats["updated"] += 1
                    else:
                        # Create new product
                        product = Product(**product_data)
                        db.add(product)
                        stats["saved"] += 1

                except Exception as e:
                    logger.error(f"Error saving product: {e}")
                    stats["failed"] += 1

            db.commit()

        except Exception as e:
            logger.error(f"Database error: {e}")
            db.rollback()
        finally:
            db.close()

        logger.info(f"Products saved: {stats}")
        return stats

    def scrape_all_categories(
        self,
        platform: str = "amazon_us",
        categories: List[str] = None,
        max_per_category: int = 30,
    ) -> Dict[str, Any]:
        """
        Scrape all categories from a platform.

        Args:
            platform: Platform to scrape
            categories: Categories to scrape (default: all)
            max_per_category: Max products per category

        Returns:
            Scraping statistics
        """
        db = SessionLocal()
        
        if not categories:
            categories = [c["id"] for c in APPAREL_CATEGORIES[:5]]  # Top 5 categories

        # Create scrape job
        job = EcommerceScrapeJob(
            platform=platform,
            status="running",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id
        db.close()

        all_products = []
        errors = []

        for category in categories:
            try:
                if platform.startswith("amazon"):
                    region = platform.split("_")[1]
                    products = self.scrape_amazon(category, region, max_per_category)
                elif platform == "hktv_mall":
                    products = self.scrape_hktv_mall(category, max_per_category)
                else:
                    products = []

                all_products.extend(products)
                logger.info(f"Category {category}: {len(products)} products")

            except Exception as e:
                error_msg = f"Error scraping {category}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Save products
        save_stats = self.save_products(all_products)

        # Update job status
        db = SessionLocal()
        job = db.query(EcommerceScrapeJob).filter(EcommerceScrapeJob.id == job_id).first()
        if job:
            job.status = "completed" if not errors else "completed_with_errors"
            job.products_found = len(all_products)
            job.products_saved = save_stats["saved"] + save_stats["updated"]
            job.error_message = "\n".join(errors) if errors else None
            job.completed_at = datetime.utcnow()
            db.commit()
        db.close()

        return {
            "job_id": job_id,
            "platform": platform,
            "categories_scraped": len(categories),
            "products_found": len(all_products),
            **save_stats,
        }

    def close(self):
        """Close the HTTP client."""
        self.client.close()
