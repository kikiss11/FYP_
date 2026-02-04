"""Streamlit Dashboard for E-Commerce Product Analysis."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
import statistics

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ecommerce.models import Product, PriceHistory, CategoryStats
from src.ecommerce.config import PLATFORMS, APPAREL_CATEGORIES, PRICE_RANGES
from src.models import SessionLocal


# Page config
st.set_page_config(
    page_title="E-Commerce Apparel Analyzer",
    page_icon="👗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #e91e63 0%, #9c27b0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .product-card {
        background: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .price-tag {
        font-size: 1.5rem;
        font-weight: bold;
        color: #e91e63;
    }
    .discount-badge {
        background: #ff5722;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.8rem;
    }
    .rating-stars {
        color: #ffc107;
    }
</style>
""", unsafe_allow_html=True)


def get_db_session() -> Session:
    """Get database session."""
    return SessionLocal()


@st.cache_data(ttl=120)
def load_overview_stats() -> dict:
    """Load overview statistics."""
    db = get_db_session()
    
    try:
        total = db.query(Product).count()
        
        # By platform
        platforms = db.query(
            Product.platform,
            func.count(Product.id),
            func.avg(Product.price),
            func.avg(Product.rating),
        ).group_by(Product.platform).all()
        
        # By category
        categories = db.query(
            Product.category,
            func.count(Product.id),
            func.avg(Product.price),
        ).group_by(Product.category).all()
        
        # Overall stats
        price_stats = db.query(
            func.avg(Product.price),
            func.min(Product.price),
            func.max(Product.price),
        ).filter(Product.price.isnot(None)).first()
        
        rating_stats = db.query(
            func.avg(Product.rating),
        ).filter(Product.rating.isnot(None)).first()
        
        return {
            "total": total,
            "platforms": [
                {"name": p, "count": c, "avg_price": round(ap or 0, 2), "avg_rating": round(ar or 0, 2)}
                for p, c, ap, ar in platforms
            ],
            "categories": [
                {"name": c, "count": n, "avg_price": round(ap or 0, 2)}
                for c, n, ap in categories
            ],
            "avg_price": round(price_stats[0] or 0, 2),
            "min_price": round(price_stats[1] or 0, 2),
            "max_price": round(price_stats[2] or 0, 2),
            "avg_rating": round(rating_stats[0] or 0, 2),
        }
    finally:
        db.close()


@st.cache_data(ttl=120)
def load_products(
    category: str = None,
    platform: str = None,
    sort_by: str = "rating",
    limit: int = 50,
) -> list:
    """Load products with filters."""
    db = get_db_session()
    
    try:
        query = db.query(Product)
        
        if category:
            query = query.filter(Product.category == category)
        if platform:
            query = query.filter(Product.platform == platform)
        
        # Sorting
        if sort_by == "rating":
            query = query.filter(Product.rating.isnot(None))
            query = query.order_by(Product.rating.desc())
        elif sort_by == "price_low":
            query = query.filter(Product.price.isnot(None))
            query = query.order_by(Product.price.asc())
        elif sort_by == "price_high":
            query = query.filter(Product.price.isnot(None))
            query = query.order_by(Product.price.desc())
        elif sort_by == "discount":
            query = query.filter(Product.discount_percent.isnot(None))
            query = query.order_by(Product.discount_percent.desc())
        elif sort_by == "reviews":
            query = query.order_by(Product.review_count.desc())
        
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


@st.cache_data(ttl=120)
def load_category_data(category: str) -> dict:
    """Load detailed category data."""
    db = get_db_session()
    
    try:
        products = db.query(Product).filter(Product.category == category).all()
        
        if not products:
            return {"error": "No products found"}
        
        prices = [p.price for p in products if p.price]
        ratings = [p.rating for p in products if p.rating]
        
        # Brand distribution
        from collections import Counter
        brands = Counter(p.brand for p in products if p.brand)
        
        # Price distribution
        price_dist = {r["id"]: 0 for r in PRICE_RANGES}
        for price in prices:
            for r in PRICE_RANGES:
                if r["min"] <= price < r["max"]:
                    price_dist[r["id"]] += 1
                    break
        
        return {
            "total": len(products),
            "prices": prices,
            "ratings": ratings,
            "avg_price": round(statistics.mean(prices), 2) if prices else 0,
            "median_price": round(statistics.median(prices), 2) if prices else 0,
            "avg_rating": round(statistics.mean(ratings), 2) if ratings else 0,
            "top_brands": brands.most_common(10),
            "price_distribution": price_dist,
            "discounted": len([p for p in products if p.discount_percent]),
        }
    finally:
        db.close()


@st.cache_data(ttl=120)
def load_brand_data(limit: int = 15) -> pd.DataFrame:
    """Load brand analysis data."""
    db = get_db_session()
    
    try:
        products = db.query(Product).filter(Product.brand.isnot(None)).all()
        
        from collections import defaultdict
        brand_data = defaultdict(lambda: {"prices": [], "ratings": [], "count": 0})
        
        for p in products:
            if p.brand:
                brand_data[p.brand]["count"] += 1
                if p.price:
                    brand_data[p.brand]["prices"].append(p.price)
                if p.rating:
                    brand_data[p.brand]["ratings"].append(p.rating)
        
        rows = []
        for brand, data in brand_data.items():
            if data["count"] >= 2:
                rows.append({
                    "Brand": brand,
                    "Products": data["count"],
                    "Avg Price": round(statistics.mean(data["prices"]), 2) if data["prices"] else 0,
                    "Avg Rating": round(statistics.mean(data["ratings"]), 2) if data["ratings"] else 0,
                })
        
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.nlargest(limit, "Products")
        return df
        
    finally:
        db.close()


def render_sidebar():
    """Render sidebar filters."""
    st.sidebar.markdown("## 🔧 Filters")
    
    # Category filter
    category_options = ["All"] + [c["name"] for c in APPAREL_CATEGORIES]
    selected_category = st.sidebar.selectbox(
        "👗 Category",
        options=category_options,
        index=0,
    )
    category_id = None
    if selected_category != "All":
        category_id = next(
            (c["id"] for c in APPAREL_CATEGORIES if c["name"] == selected_category),
            None
        )
    
    # Platform filter
    platform_options = ["All"] + [v["name"] for v in PLATFORMS.values()]
    selected_platform = st.sidebar.selectbox(
        "🏪 Platform",
        options=platform_options,
        index=0,
    )
    platform_id = None
    if selected_platform != "All":
        platform_id = next(
            (k for k, v in PLATFORMS.items() if v["name"] == selected_platform),
            None
        )
    
    # Sort by
    sort_options = {
        "⭐ Rating": "rating",
        "💰 Price (Low to High)": "price_low",
        "💎 Price (High to Low)": "price_high",
        "🔥 Discount": "discount",
        "💬 Reviews": "reviews",
    }
    selected_sort = st.sidebar.selectbox(
        "📊 Sort By",
        options=list(sort_options.keys()),
        index=0,
    )
    sort_by = sort_options[selected_sort]
    
    st.sidebar.markdown("---")
    
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    return {
        "category": category_id,
        "platform": platform_id,
        "sort_by": sort_by,
    }


def render_overview():
    """Render overview section."""
    st.markdown('<h1 class="main-header">👗 E-Commerce Apparel Analyzer</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Women\'s fashion price & review analysis across platforms</p>', unsafe_allow_html=True)
    
    stats = load_overview_stats()
    
    if stats["total"] == 0:
        st.warning("No products in database. Click 'Generate Sample Data' to create demo data.")
        if st.button("🎲 Generate Sample Data"):
            import httpx
            try:
                response = httpx.post(
                    "http://localhost:8000/ecommerce/sample/generate",
                    json={"products_per_category": 25},
                    timeout=60,
                )
                if response.status_code == 200:
                    st.success("Sample data generated! Refresh the page.")
                    st.cache_data.clear()
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
        return
    
    # Metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📦 Total Products", f"{stats['total']:,}")
    with col2:
        st.metric("💰 Avg Price", f"${stats['avg_price']:.2f}")
    with col3:
        st.metric("📊 Price Range", f"${stats['min_price']:.0f} - ${stats['max_price']:.0f}")
    with col4:
        st.metric("⭐ Avg Rating", f"{stats['avg_rating']:.1f}/5")
    with col5:
        st.metric("🏪 Platforms", len(stats["platforms"]))


def render_platform_comparison():
    """Render platform comparison charts."""
    st.markdown("## 🏪 Platform Comparison")
    
    stats = load_overview_stats()
    
    if not stats["platforms"]:
        st.info("No platform data available.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Product count by platform
        df = pd.DataFrame(stats["platforms"])
        if not df.empty:
            fig = px.pie(
                df,
                values="count",
                names="name",
                title="Products by Platform",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Average price by platform
        if not df.empty:
            fig = px.bar(
                df,
                x="name",
                y="avg_price",
                color="avg_rating",
                title="Avg Price & Rating by Platform",
                color_continuous_scale="RdYlGn",
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)


def render_category_analysis():
    """Render category analysis."""
    st.markdown("## 👗 Category Analysis")
    
    stats = load_overview_stats()
    
    if not stats["categories"]:
        st.info("No category data available.")
        return
    
    # Category overview
    df = pd.DataFrame(stats["categories"])
    
    if not df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(
                df.nlargest(10, "count"),
                x="count",
                y="name",
                orientation="h",
                title="Products by Category",
                color="avg_price",
                color_continuous_scale="Viridis",
            )
            fig.update_layout(height=400, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.scatter(
                df,
                x="count",
                y="avg_price",
                size="count",
                text="name",
                title="Category: Count vs Price",
                color="avg_price",
                color_continuous_scale="Plasma",
            )
            fig.update_traces(textposition="top center")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)


def render_brand_analysis():
    """Render brand analysis."""
    st.markdown("## 🏷️ Brand Analysis")
    
    df = load_brand_data(20)
    
    if df.empty:
        st.info("No brand data available.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.bar(
            df.nlargest(15, "Products"),
            x="Products",
            y="Brand",
            orientation="h",
            title="Top Brands by Product Count",
            color="Avg Rating",
            color_continuous_scale="RdYlGn",
        )
        fig.update_layout(height=500, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.scatter(
            df,
            x="Avg Price",
            y="Avg Rating",
            size="Products",
            text="Brand",
            title="Brand: Price vs Rating",
            color="Products",
            color_continuous_scale="Blues",
        )
        fig.update_traces(textposition="top center", textfont_size=8)
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)


def render_price_distribution():
    """Render price distribution analysis."""
    st.markdown("## 💰 Price Distribution")
    
    stats = load_overview_stats()
    
    if not stats["categories"]:
        return
    
    # Get all products
    products = load_products(limit=500)
    
    if not products:
        return
    
    prices = [p["price"] for p in products if p["price"]]
    
    if not prices:
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Price histogram
        fig = px.histogram(
            x=prices,
            nbins=30,
            title="Price Distribution",
            labels={"x": "Price ($)", "y": "Count"},
            color_discrete_sequence=["#e91e63"],
        )
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Price by category box plot
        df = pd.DataFrame(products)
        if not df.empty and "category" in df.columns:
            fig = px.box(
                df[df["price"].notna()],
                x="category",
                y="price",
                title="Price Range by Category",
                color="category",
            )
            fig.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)


def render_products_list(filters: dict):
    """Render products list."""
    st.markdown("## 🛍️ Products")
    
    products = load_products(
        category=filters["category"],
        platform=filters["platform"],
        sort_by=filters["sort_by"],
        limit=30,
    )
    
    if not products:
        st.info("No products found with current filters.")
        return
    
    # Display in grid
    cols = st.columns(3)
    
    for idx, product in enumerate(products):
        with cols[idx % 3]:
            with st.container():
                # Product card
                st.markdown(f"**{product['name'][:60]}{'...' if len(product['name']) > 60 else ''}**")
                
                if product.get("brand"):
                    st.caption(f"🏷️ {product['brand']}")
                
                # Price
                price_col, rating_col = st.columns(2)
                with price_col:
                    if product.get("discount_percent"):
                        st.markdown(f"~~${product['original_price']:.2f}~~ **${product['price']:.2f}**")
                        st.markdown(f"🔥 {product['discount_percent']:.0f}% OFF")
                    elif product.get("price"):
                        st.markdown(f"**${product['price']:.2f}**")
                
                with rating_col:
                    if product.get("rating"):
                        stars = "⭐" * int(product["rating"])
                        st.markdown(f"{stars} {product['rating']:.1f}")
                    if product.get("review_count"):
                        st.caption(f"💬 {product['review_count']:,} reviews")
                
                # Platform badge
                platform_name = PLATFORMS.get(product["platform"], {}).get("name", product["platform"])
                st.caption(f"🏪 {platform_name}")
                
                if product.get("is_bestseller"):
                    st.success("🏆 Bestseller")
                
                st.markdown("---")


def main():
    """Main dashboard entry point."""
    filters = render_sidebar()
    
    render_overview()
    st.markdown("---")
    
    render_platform_comparison()
    st.markdown("---")
    
    render_category_analysis()
    st.markdown("---")
    
    render_brand_analysis()
    st.markdown("---")
    
    render_price_distribution()
    st.markdown("---")
    
    render_products_list(filters)
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666; padding: 1rem;">
            👗 E-Commerce Apparel Analyzer | Price & Review Analysis
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
