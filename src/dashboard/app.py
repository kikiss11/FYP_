"""Streamlit Dashboard for Google Trends Data Visualization."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import func
from sqlalchemy.orm import Session

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models import (
    InterestByRegion,
    RelatedQuery,
    RelatedTopic,
    ScrapeJob,
    SessionLocal,
    TrendData,
)
from src.config import trends_config

# Page config
st.set_page_config(
    page_title="Google Trends Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        color: white;
    }
    .stMetric {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


def get_db_session() -> Session:
    """Get database session."""
    return SessionLocal()


@st.cache_data(ttl=60)
def load_trend_data(keyword: str = None, region: str = None) -> pd.DataFrame:
    """Load trend data from database."""
    db = get_db_session()
    try:
        query = db.query(
            TrendData.keyword,
            TrendData.region_code,
            TrendData.region_name,
            TrendData.date,
            TrendData.interest,
        )
        if keyword:
            query = query.filter(TrendData.keyword == keyword)
        if region:
            query = query.filter(TrendData.region_code == region)

        results = query.order_by(TrendData.date.desc()).all()

        if results:
            df = pd.DataFrame(results, columns=[
                "keyword", "region_code", "region_name", "date", "interest"
            ])
            df["date"] = pd.to_datetime(df["date"])
            return df
        return pd.DataFrame()
    finally:
        db.close()


@st.cache_data(ttl=60)
def load_related_queries(keyword: str = None, region: str = None) -> pd.DataFrame:
    """Load related queries from database."""
    db = get_db_session()
    try:
        query = db.query(
            RelatedQuery.keyword,
            RelatedQuery.region_code,
            RelatedQuery.query_type,
            RelatedQuery.query_text,
            RelatedQuery.value,
        )
        if keyword:
            query = query.filter(RelatedQuery.keyword == keyword)
        if region:
            query = query.filter(RelatedQuery.region_code == region)

        results = query.all()
        if results:
            return pd.DataFrame(results, columns=[
                "keyword", "region_code", "query_type", "query_text", "value"
            ])
        return pd.DataFrame()
    finally:
        db.close()


@st.cache_data(ttl=60)
def load_related_topics(keyword: str = None, region: str = None) -> pd.DataFrame:
    """Load related topics from database."""
    db = get_db_session()
    try:
        query = db.query(
            RelatedTopic.keyword,
            RelatedTopic.region_code,
            RelatedTopic.topic_type,
            RelatedTopic.topic_title,
            RelatedTopic.topic_category,
            RelatedTopic.value,
        )
        if keyword:
            query = query.filter(RelatedTopic.keyword == keyword)
        if region:
            query = query.filter(RelatedTopic.region_code == region)

        results = query.all()
        if results:
            return pd.DataFrame(results, columns=[
                "keyword", "region_code", "topic_type", "topic_title", "topic_category", "value"
            ])
        return pd.DataFrame()
    finally:
        db.close()


@st.cache_data(ttl=60)
def get_unique_values() -> dict:
    """Get unique keywords and regions from database."""
    db = get_db_session()
    try:
        keywords = [r[0] for r in db.query(TrendData.keyword).distinct().all()]
        regions = [
            {"code": r[0], "name": r[1]}
            for r in db.query(TrendData.region_code, TrendData.region_name).distinct().all()
        ]
        return {"keywords": keywords, "regions": regions}
    finally:
        db.close()


@st.cache_data(ttl=30)
def get_job_stats() -> dict:
    """Get scrape job statistics."""
    db = get_db_session()
    try:
        total_jobs = db.query(ScrapeJob).count()
        completed_jobs = db.query(ScrapeJob).filter(ScrapeJob.status == "completed").count()
        latest_job = db.query(ScrapeJob).order_by(ScrapeJob.started_at.desc()).first()
        total_data_points = db.query(TrendData).count()

        return {
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "latest_job": latest_job,
            "total_data_points": total_data_points,
        }
    finally:
        db.close()


def render_sidebar():
    """Render sidebar with filters."""
    st.sidebar.markdown("## 🔧 Filters")

    unique_vals = get_unique_values()
    keywords = unique_vals.get("keywords", trends_config.keywords)
    regions = unique_vals.get("regions", [{"code": r["code"], "name": r["name"]} for r in trends_config.regions])

    if not keywords:
        keywords = trends_config.keywords
    if not regions:
        regions = trends_config.regions

    selected_keyword = st.sidebar.selectbox(
        "📝 Keyword",
        options=["All"] + keywords,
        index=0,
    )

    region_options = ["All"] + [f"{r['code']} - {r['name']}" for r in regions]
    selected_region = st.sidebar.selectbox(
        "🌍 Region",
        options=region_options,
        index=0,
    )

    # Parse region code
    region_code = None
    if selected_region != "All":
        region_code = selected_region.split(" - ")[0]

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📅 Configuration")
    st.sidebar.info(f"""
    **Tracked Keywords:** {', '.join(trends_config.keywords)}

    **Tracked Regions:** {', '.join([r['code'] for r in trends_config.regions])}

    **Timeframe:** {trends_config.timeframe}
    """)

    return {
        "keyword": None if selected_keyword == "All" else selected_keyword,
        "region": region_code,
    }


def render_overview():
    """Render overview metrics."""
    st.markdown('<h1 class="main-header">📊 Google Trends Dashboard</h1>', unsafe_allow_html=True)
    
    # Refresh button
    col_title, col_refresh = st.columns([4, 1])
    with col_title:
        st.markdown('<p class="sub-header">Track fashion keyword trends across regions</p>', unsafe_allow_html=True)
    with col_refresh:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

    stats = get_job_stats()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Jobs", stats["total_jobs"])
    with col2:
        st.metric("Completed Jobs", stats["completed_jobs"])
    with col3:
        st.metric("Data Points", f"{stats['total_data_points']:,}")
    with col4:
        if stats["latest_job"]:
            st.metric("Last Run", stats["latest_job"].started_at.strftime("%Y-%m-%d %H:%M"))
        else:
            st.metric("Last Run", "Never")
    
    # Show tracked regions summary
    unique_vals = get_unique_values()
    if unique_vals.get("regions"):
        regions_list = [r["code"] for r in unique_vals["regions"] if r["code"]]
        if regions_list:
            st.success(f"**📍 Regions with data:** {', '.join(regions_list)}")
    if unique_vals.get("keywords"):
        st.info(f"**🔑 Keywords tracked:** {', '.join(unique_vals['keywords'])}")


def render_interest_over_time(filters: dict):
    """Render interest over time chart."""
    st.markdown("## 📈 Interest Over Time")

    df = load_trend_data(keyword=filters["keyword"], region=filters["region"])

    if df.empty:
        st.warning("No trend data available. Run an extraction first!")
        return

    # Create line chart
    if filters["keyword"]:
        # Single keyword - compare regions
        fig = px.line(
            df,
            x="date",
            y="interest",
            color="region_name",
            title=f"Interest Over Time: {filters['keyword']}",
            labels={"interest": "Interest (0-100)", "date": "Date", "region_name": "Region"},
        )
    elif filters["region"]:
        # Single region - compare keywords
        fig = px.line(
            df,
            x="date",
            y="interest",
            color="keyword",
            title=f"Interest Over Time: {filters['region']}",
            labels={"interest": "Interest (0-100)", "date": "Date", "keyword": "Keyword"},
        )
    else:
        # All data - facet by keyword
        fig = px.line(
            df,
            x="date",
            y="interest",
            color="region_name",
            facet_col="keyword",
            title="Interest Over Time by Keyword and Region",
            labels={"interest": "Interest (0-100)", "date": "Date"},
        )

    fig.update_layout(
        height=500,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    st.plotly_chart(fig, use_container_width=True)


def render_related_queries(filters: dict):
    """Render related queries tables."""
    st.markdown("## 🔍 Related Searches")

    df = load_related_queries(keyword=filters["keyword"], region=filters["region"])

    if df.empty:
        st.info("No related queries data available.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🔝 Top Queries")
        top_df = df[df["query_type"] == "top"].sort_values("value", ascending=False).head(20)
        if not top_df.empty:
            fig = px.bar(
                top_df,
                x="value",
                y="query_text",
                orientation="h",
                color="keyword",
                title="Top Related Queries",
            )
            fig.update_layout(height=400, template="plotly_white", yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No top queries found.")

    with col2:
        st.markdown("### 📈 Rising Queries")
        rising_df = df[df["query_type"] == "rising"].sort_values("value", ascending=False).head(20)
        if not rising_df.empty:
            fig = px.bar(
                rising_df,
                x="value",
                y="query_text",
                orientation="h",
                color="keyword",
                title="Rising Related Queries",
            )
            fig.update_layout(height=400, template="plotly_white", yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No rising queries found.")


def render_related_topics(filters: dict):
    """Render related topics."""
    st.markdown("## 🏷️ Related Topics/Themes")

    df = load_related_topics(keyword=filters["keyword"], region=filters["region"])

    if df.empty:
        st.info("No related topics data available.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🔝 Top Topics")
        top_df = df[df["topic_type"] == "top"].sort_values("value", ascending=False).head(15)
        if not top_df.empty:
            st.dataframe(
                top_df[["topic_title", "topic_category", "keyword", "value"]].rename(columns={
                    "topic_title": "Topic",
                    "topic_category": "Category",
                    "keyword": "Keyword",
                    "value": "Interest",
                }),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No top topics found.")

    with col2:
        st.markdown("### 📈 Rising Topics")
        rising_df = df[df["topic_type"] == "rising"].sort_values("value", ascending=False).head(15)
        if not rising_df.empty:
            st.dataframe(
                rising_df[["topic_title", "topic_category", "keyword", "value"]].rename(columns={
                    "topic_title": "Topic",
                    "topic_category": "Category",
                    "keyword": "Keyword",
                    "value": "Growth %",
                }),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No rising topics found.")


def render_comparison():
    """Render keyword comparison."""
    st.markdown("## 📊 Keyword Comparison")

    df = load_trend_data()

    if df.empty:
        st.info("No data available for comparison.")
        return

    # Average interest by keyword
    avg_df = df.groupby("keyword")["interest"].mean().reset_index()
    avg_df.columns = ["Keyword", "Average Interest"]

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            avg_df,
            x="Keyword",
            y="Average Interest",
            color="Keyword",
            title="Average Interest by Keyword",
        )
        fig.update_layout(height=400, template="plotly_white", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Interest by region
        region_df = df.groupby("region_code")["interest"].mean().reset_index()
        region_df.columns = ["Region", "Average Interest"]

        fig = px.pie(
            region_df,
            values="Average Interest",
            names="Region",
            title="Interest Distribution by Region",
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)


def main():
    """Main dashboard entry point."""
    # Sidebar filters
    filters = render_sidebar()

    # Main content
    render_overview()
    st.markdown("---")
    render_interest_over_time(filters)
    st.markdown("---")
    render_related_queries(filters)
    st.markdown("---")
    render_related_topics(filters)
    st.markdown("---")
    render_comparison()

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666; padding: 1rem;">
            📊 Google Trends Scraper Dashboard | Built with Streamlit & Plotly
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

