"""Configuration for E-Commerce Analyzer."""

from typing import List, Dict

# Supported platforms
PLATFORMS = {
    "amazon_us": {
        "name": "Amazon US",
        "base_url": "https://www.amazon.com",
        "currency": "USD",
        "region": "US",
    },
    "amazon_uk": {
        "name": "Amazon UK",
        "base_url": "https://www.amazon.co.uk",
        "currency": "GBP",
        "region": "GB",
    },
    "amazon_jp": {
        "name": "Amazon Japan",
        "base_url": "https://www.amazon.co.jp",
        "currency": "JPY",
        "region": "JP",
    },
    "hktv_mall": {
        "name": "HKTV Mall",
        "base_url": "https://www.hktvmall.com",
        "currency": "HKD",
        "region": "HK",
    },
}

# Women's apparel categories
APPAREL_CATEGORIES = [
    {"id": "dresses", "name": "Dresses", "keywords": ["dress", "gown", "frock"]},
    {"id": "tops", "name": "Tops & Blouses", "keywords": ["top", "blouse", "shirt", "t-shirt", "tee"]},
    {"id": "pants", "name": "Pants & Trousers", "keywords": ["pants", "trousers", "jeans", "leggings"]},
    {"id": "skirts", "name": "Skirts", "keywords": ["skirt", "mini skirt", "maxi skirt"]},
    {"id": "jackets", "name": "Jackets & Coats", "keywords": ["jacket", "coat", "blazer", "cardigan"]},
    {"id": "sweaters", "name": "Sweaters & Knitwear", "keywords": ["sweater", "pullover", "knitwear"]},
    {"id": "activewear", "name": "Activewear", "keywords": ["activewear", "sportswear", "yoga", "gym"]},
    {"id": "swimwear", "name": "Swimwear", "keywords": ["swimwear", "bikini", "swimsuit"]},
    {"id": "lingerie", "name": "Lingerie & Underwear", "keywords": ["lingerie", "underwear", "bra"]},
    {"id": "accessories", "name": "Accessories", "keywords": ["scarf", "belt", "hat", "bag"]},
]

# Price ranges for analysis
PRICE_RANGES = [
    {"id": "budget", "name": "Budget", "min": 0, "max": 25},
    {"id": "affordable", "name": "Affordable", "min": 25, "max": 50},
    {"id": "mid_range", "name": "Mid-Range", "min": 50, "max": 100},
    {"id": "premium", "name": "Premium", "min": 100, "max": 200},
    {"id": "luxury", "name": "Luxury", "min": 200, "max": float("inf")},
]

# Scraping settings
SCRAPE_DELAY = 3  # Seconds between requests
MAX_PRODUCTS_PER_CATEGORY = 50
REQUEST_TIMEOUT = 30
