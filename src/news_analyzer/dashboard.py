"""Streamlit Dashboard for Tariff News Analysis."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.news_analyzer.models import (
    NewsArticle,
    NewsAnalysis,
    NewsEntity,
    TradeTensionReport,
)
from src.news_analyzer.config import ANALYSIS_REGIONS
from src.models import SessionLocal


# Page config
st.set_page_config(
    page_title="Tariff News Analyzer",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .tension-high {
        background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
    }
    .tension-moderate {
        background: linear-gradient(135deg, #ffc107 0%, #e0a800 100%);
        color: black;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
    }
    .tension-low {
        background: linear-gradient(135deg, #28a745 0%, #218838 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 1rem;
        border-left: 4px solid #1e3a5f;
    }
    .news-card {
        background: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def get_db_session() -> Session:
    """Get database session."""
    return SessionLocal()


@st.cache_data(ttl=60)
def load_analysis_stats(days_back: int = 30) -> dict:
    """Load analysis statistics."""
    db = get_db_session()
    start_date = datetime.utcnow() - timedelta(days=days_back)

    try:
        # Total counts
        total_articles = db.query(NewsArticle).filter(
            NewsArticle.published_at >= start_date
        ).count()

        analyzed_articles = db.query(NewsAnalysis).join(NewsArticle).filter(
            NewsArticle.published_at >= start_date
        ).count()

        # Sentiment distribution
        sentiments = db.query(
            NewsAnalysis.sentiment,
            func.count(NewsAnalysis.id)
        ).join(NewsArticle).filter(
            NewsArticle.published_at >= start_date
        ).group_by(NewsAnalysis.sentiment).all()

        # Tension distribution
        tensions = db.query(
            NewsAnalysis.tension_level,
            func.count(NewsAnalysis.id)
        ).join(NewsArticle).filter(
            NewsArticle.published_at >= start_date
        ).group_by(NewsAnalysis.tension_level).all()

        # Average scores
        avg_scores = db.query(
            func.avg(NewsAnalysis.sentiment_score),
            func.avg(NewsAnalysis.tension_score),
            func.avg(NewsAnalysis.effectiveness_score),
        ).join(NewsArticle).filter(
            NewsArticle.published_at >= start_date
        ).first()

        return {
            "total_articles": total_articles,
            "analyzed_articles": analyzed_articles,
            "sentiments": dict(sentiments),
            "tensions": dict(tensions),
            "avg_sentiment": avg_scores[0] or 0,
            "avg_tension": avg_scores[1] or 0,
            "avg_effectiveness": avg_scores[2] or 0,
        }

    finally:
        db.close()


@st.cache_data(ttl=60)
def load_tension_trend(days_back: int = 30, region: str = None) -> pd.DataFrame:
    """Load tension trend data."""
    db = get_db_session()
    start_date = datetime.utcnow() - timedelta(days=days_back)

    try:
        query = db.query(
            func.date(NewsArticle.published_at).label("date"),
            func.avg(NewsAnalysis.tension_score).label("tension"),
            func.avg(NewsAnalysis.sentiment_score).label("sentiment"),
            func.count(NewsAnalysis.id).label("count"),
        ).join(NewsArticle).filter(
            NewsArticle.published_at >= start_date
        )

        if region:
            query = query.filter(NewsAnalysis.primary_region == region)

        results = query.group_by(
            func.date(NewsArticle.published_at)
        ).order_by(func.date(NewsArticle.published_at)).all()

        if results:
            df = pd.DataFrame([
                {
                    "date": r.date,
                    "tension": r.tension or 0,
                    "sentiment": r.sentiment or 0,
                    "count": r.count,
                }
                for r in results
            ])
            df["date"] = pd.to_datetime(df["date"])
            return df

        return pd.DataFrame()

    finally:
        db.close()


@st.cache_data(ttl=60)
def load_region_stats(days_back: int = 30) -> pd.DataFrame:
    """Load statistics by region."""
    db = get_db_session()
    start_date = datetime.utcnow() - timedelta(days=days_back)

    try:
        results = db.query(
            NewsAnalysis.primary_region,
            func.count(NewsAnalysis.id).label("count"),
            func.avg(NewsAnalysis.tension_score).label("avg_tension"),
            func.avg(NewsAnalysis.sentiment_score).label("avg_sentiment"),
        ).join(NewsArticle).filter(
            and_(
                NewsArticle.published_at >= start_date,
                NewsAnalysis.primary_region.isnot(None),
            )
        ).group_by(NewsAnalysis.primary_region).all()

        if results:
            df = pd.DataFrame([
                {
                    "region": r.primary_region,
                    "article_count": r.count,
                    "avg_tension": r.avg_tension or 0,
                    "avg_sentiment": r.avg_sentiment or 0,
                }
                for r in results
            ])
            # Add region names
            region_map = {r["code"]: r["name"] for r in ANALYSIS_REGIONS}
            df["region_name"] = df["region"].map(region_map).fillna(df["region"])
            return df

        return pd.DataFrame()

    finally:
        db.close()


@st.cache_data(ttl=60)
def load_top_entities(days_back: int = 30, entity_type: str = "ORG", limit: int = 15) -> pd.DataFrame:
    """Load top entities."""
    db = get_db_session()
    start_date = datetime.utcnow() - timedelta(days=days_back)

    try:
        # Get article IDs in date range
        article_ids = db.query(NewsArticle.id).filter(
            NewsArticle.published_at >= start_date
        ).all()
        article_ids = [a.id for a in article_ids]

        if not article_ids:
            return pd.DataFrame()

        # Get entities
        results = db.query(
            NewsEntity.entity_text,
            func.sum(NewsEntity.count).label("total_count")
        ).filter(
            and_(
                NewsEntity.article_id.in_(article_ids),
                NewsEntity.entity_type == entity_type,
            )
        ).group_by(NewsEntity.entity_text).order_by(
            func.sum(NewsEntity.count).desc()
        ).limit(limit).all()

        if results:
            return pd.DataFrame([
                {"entity": r.entity_text, "count": r.total_count}
                for r in results
            ])

        return pd.DataFrame()

    finally:
        db.close()


@st.cache_data(ttl=60)
def load_recent_articles(limit: int = 10, tension_filter: str = None) -> list:
    """Load recent analyzed articles."""
    db = get_db_session()

    try:
        query = db.query(NewsAnalysis, NewsArticle).join(NewsArticle)

        if tension_filter:
            query = query.filter(NewsAnalysis.tension_level == tension_filter)

        results = query.order_by(
            NewsArticle.published_at.desc()
        ).limit(limit).all()

        return [
            {
                "title": article.title,
                "source": article.source_name,
                "url": article.url,
                "published_at": article.published_at,
                "description": article.description[:200] if article.description else "",
                "sentiment": analysis.sentiment,
                "sentiment_score": analysis.sentiment_score,
                "tension_level": analysis.tension_level,
                "tension_score": analysis.tension_score,
                "primary_region": analysis.primary_region,
                "regions_mentioned": analysis.regions_mentioned or [],
                "keywords": analysis.keywords_extracted[:5] if analysis.keywords_extracted else [],
                "tension_keywords": analysis.tension_keywords or {},
                "trade_summary": analysis.summary,  # LLM-generated summary
            }
            for analysis, article in results
        ]

    finally:
        db.close()


@st.cache_data(ttl=60)
def load_top_keywords(days_back: int = 30, limit: int = 20) -> list:
    """Load most frequent keywords from analyzed articles."""
    db = get_db_session()
    start_date = datetime.utcnow() - timedelta(days=days_back)

    try:
        results = db.query(NewsAnalysis).join(NewsArticle).filter(
            NewsArticle.published_at >= start_date
        ).all()

        # Aggregate keywords
        from collections import Counter
        keyword_counter = Counter()
        for analysis in results:
            if analysis.keywords_extracted:
                for kw in analysis.keywords_extracted:
                    if kw and len(kw) > 2:
                        keyword_counter[kw] += 1

        return keyword_counter.most_common(limit)

    finally:
        db.close()


def render_sidebar():
    """Render sidebar."""
    st.sidebar.markdown("## 🔧 Filters")

    days_back = st.sidebar.slider(
        "📅 Time Period (days)",
        min_value=1,
        max_value=90,
        value=30,
    )

    # Region filter
    region_options = ["All"] + [
        f"{r['code']} - {r['name']}" for r in ANALYSIS_REGIONS
    ]
    selected_region = st.sidebar.selectbox(
        "🌍 Region",
        options=region_options,
        index=0,
    )

    region_code = None
    if selected_region != "All":
        region_code = selected_region.split(" - ")[0]

    # Tension filter
    tension_filter = st.sidebar.selectbox(
        "⚡ Tension Level",
        options=["All", "high", "moderate", "low", "positive"],
        index=0,
    )

    if tension_filter == "All":
        tension_filter = None

    st.sidebar.markdown("---")

    # Refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    return {
        "days_back": days_back,
        "region": region_code,
        "tension": tension_filter,
    }


def render_overview(days_back: int):
    """Render overview section."""
    st.markdown('<h1 class="main-header">📰 Tariff News Analyzer</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Track trade tensions and effectiveness from news</p>', unsafe_allow_html=True)

    stats = load_analysis_stats(days_back)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("📄 Total Articles", stats["total_articles"])
    with col2:
        st.metric("🔍 Analyzed", stats["analyzed_articles"])
    with col3:
        sentiment_emoji = "😊" if stats["avg_sentiment"] > 0 else "😟" if stats["avg_sentiment"] < 0 else "😐"
        st.metric(f"{sentiment_emoji} Avg Sentiment", f"{stats['avg_sentiment']:.2f}")
    with col4:
        tension_emoji = "🔥" if stats["avg_tension"] > 0.5 else "⚠️" if stats["avg_tension"] > 0.2 else "✅"
        st.metric(f"{tension_emoji} Avg Tension", f"{stats['avg_tension']:.2f}")
    with col5:
        eff_emoji = "📈" if stats["avg_effectiveness"] > 0 else "📉" if stats["avg_effectiveness"] < 0 else "➡️"
        st.metric(f"{eff_emoji} Effectiveness", f"{stats['avg_effectiveness']:.2f}")


def render_tension_trend(days_back: int, region: str = None):
    """Render tension trend chart."""
    st.markdown("## 📈 Trade Tension Trend")

    df = load_tension_trend(days_back, region)

    if df.empty:
        st.warning("No trend data available. Fetch and analyze news first!")
        return

    # Create dual-axis chart
    fig = go.Figure()

    # Tension line
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["tension"],
        name="Tension Score",
        line=dict(color="#dc3545", width=2),
        fill="tozeroy",
        fillcolor="rgba(220, 53, 69, 0.1)",
    ))

    # Sentiment line
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["sentiment"],
        name="Sentiment Score",
        line=dict(color="#28a745", width=2),
        yaxis="y2",
    ))

    # Article count bars
    fig.add_trace(go.Bar(
        x=df["date"],
        y=df["count"],
        name="Article Count",
        marker_color="rgba(30, 58, 95, 0.3)",
        yaxis="y3",
    ))

    fig.update_layout(
        height=400,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(title="Tension Score", side="left", range=[-1, 1]),
        yaxis2=dict(title="Sentiment", side="right", overlaying="y", range=[-1, 1]),
        yaxis3=dict(title="Count", overlaying="y", anchor="free", position=0.05, visible=False),
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)


def render_region_analysis(days_back: int):
    """Render region analysis charts."""
    st.markdown("## 🌍 Analysis by Region")

    df = load_region_stats(days_back)

    if df.empty:
        st.info("No region data available.")
        return

    col1, col2 = st.columns(2)

    with col1:
        # Tension by region
        fig = px.bar(
            df.nlargest(10, "avg_tension"),
            x="region_name",
            y="avg_tension",
            color="avg_tension",
            color_continuous_scale="Reds",
            title="🔥 Trade Tension by Region",
        )
        fig.update_layout(height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Article distribution
        fig = px.pie(
            df.nlargest(10, "article_count"),
            values="article_count",
            names="region_name",
            title="📊 News Coverage by Region",
            hole=0.4,
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)


def render_sentiment_distribution(days_back: int):
    """Render sentiment and tension distribution."""
    st.markdown("## 📊 Sentiment & Tension Distribution")

    stats = load_analysis_stats(days_back)

    col1, col2 = st.columns(2)

    with col1:
        # Sentiment pie chart
        sentiments = stats["sentiments"]
        if sentiments:
            colors = {"positive": "#28a745", "negative": "#dc3545", "neutral": "#6c757d"}
            fig = go.Figure(data=[go.Pie(
                labels=list(sentiments.keys()),
                values=list(sentiments.values()),
                marker_colors=[colors.get(k, "#888") for k in sentiments.keys()],
                hole=0.4,
            )])
            fig.update_layout(title="Sentiment Distribution", height=350)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Tension distribution
        tensions = stats["tensions"]
        if tensions:
            colors = {"high": "#dc3545", "moderate": "#ffc107", "low": "#28a745", "positive": "#17a2b8"}
            fig = go.Figure(data=[go.Pie(
                labels=list(tensions.keys()),
                values=list(tensions.values()),
                marker_colors=[colors.get(k, "#888") for k in tensions.keys()],
                hole=0.4,
            )])
            fig.update_layout(title="Tension Level Distribution", height=350)
            st.plotly_chart(fig, use_container_width=True)


def render_top_entities(days_back: int):
    """Render top entities."""
    st.markdown("## 🏢 Key Players & Topics")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Organizations")
        org_df = load_top_entities(days_back, "ORG", 15)
        if not org_df.empty:
            fig = px.bar(
                org_df,
                x="count",
                y="entity",
                orientation="h",
                color="count",
                color_continuous_scale="Blues",
            )
            fig.update_layout(height=400, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No organization data available.")

    with col2:
        st.markdown("### Countries/Regions")
        gpe_df = load_top_entities(days_back, "GPE", 15)
        if not gpe_df.empty:
            fig = px.bar(
                gpe_df,
                x="count",
                y="entity",
                orientation="h",
                color="count",
                color_continuous_scale="Greens",
            )
            fig.update_layout(height=400, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No country data available.")


def render_recent_articles(tension_filter: str = None, days_back: int = 30):
    """Render recent high-tension articles with keywords sidebar."""
    st.markdown("## 📰 Recent Articles & Keywords")

    # Two column layout - articles on left, keywords on right
    col_articles, col_keywords = st.columns([3, 1])

    with col_keywords:
        st.markdown("### 🔑 Top Keywords")
        top_keywords = load_top_keywords(days_back, 25)
        if top_keywords:
            # Create a word cloud style display
            for keyword, count in top_keywords:
                # Size based on frequency
                if count > 10:
                    st.markdown(f"**`{keyword}`** ({count})")
                elif count > 5:
                    st.markdown(f"`{keyword}` ({count})")
                else:
                    st.caption(f"{keyword} ({count})")
        else:
            st.info("No keywords found.")

    with col_articles:
        articles = load_recent_articles(20, tension_filter)

        if not articles:
            st.info("No articles found.")
            return

        for article in articles:
            sentiment_emoji = "😊" if article['sentiment'] == "positive" else "😟" if article['sentiment'] == "negative" else "😐"
            
            # Tension color
            tension_color = {
                "high": "🔴",
                "moderate": "🟡", 
                "low": "🟢",
                "positive": "🔵",
            }.get(article['tension_level'], "⚪")

            with st.container():
                # Title and source
                st.markdown(f"**[{article['title'][:100]}...]({article['url']})**" if len(article['title']) > 100 else f"**[{article['title']}]({article['url']})**")
                
                # Trade Impact Summary (LLM-generated) - highlighted
                if article.get('trade_summary'):
                    st.info(f"👗 **Trade Impact:** {article['trade_summary']}")
                elif article.get('description'):
                    st.caption(article['description'][:150] + "..." if len(article['description']) > 150 else article['description'])
                
                # Metadata row
                meta_col1, meta_col2, meta_col3, meta_col4 = st.columns([2, 1, 1, 2])
                
                with meta_col1:
                    st.caption(f"📰 {article['source']} | {article['published_at'].strftime('%Y-%m-%d')}")
                
                with meta_col2:
                    st.caption(f"{tension_color} {article['tension_level'] or 'N/A'}")
                
                with meta_col3:
                    st.caption(f"{sentiment_emoji} {article['sentiment']}")
                
                with meta_col4:
                    # Show keywords for this article
                    if article.get('keywords'):
                        keywords_str = ", ".join(article['keywords'][:3])
                        st.caption(f"🏷️ {keywords_str}")
                    elif article.get('primary_region'):
                        st.caption(f"🌍 {article['primary_region']}")

                st.markdown("---")


def main():
    """Main dashboard entry point."""
    filters = render_sidebar()

    render_overview(filters["days_back"])
    st.markdown("---")

    render_tension_trend(filters["days_back"], filters["region"])
    st.markdown("---")

    render_sentiment_distribution(filters["days_back"])
    st.markdown("---")

    render_region_analysis(filters["days_back"])
    st.markdown("---")

    render_top_entities(filters["days_back"])
    st.markdown("---")

    render_recent_articles(filters["tension"], filters["days_back"])

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666; padding: 1rem;">
            📰 Tariff News Analyzer | Trade Tension & Effectiveness Analysis
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
