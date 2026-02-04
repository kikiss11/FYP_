"""Streamlit dashboard for Macroeconomic Trade Analysis - Consultant Edition."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import httpx
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import trade insights engine
import sys
from pathlib import Path
# Add parent directory to path for direct script execution
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from macro_analyzer.trade_insights import get_insights_engine, INDICATOR_IMPACTS
except ImportError:
    from trade_insights import get_insights_engine, INDICATOR_IMPACTS

# Configuration - use environment variable or default
import os
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")

st.set_page_config(
    page_title="Macro Trade Analyzer | Women's Apparel",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Playfair+Display:wght@600;700&display=swap');
    
    .main {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
    }
    
    .stApp {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
    }
    
    h1 {
        font-family: 'Playfair Display', serif !important;
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem !important;
    }
    
    h2, h3 {
        font-family: 'DM Sans', sans-serif !important;
        color: #e8d5b7 !important;
    }
    
    .metric-card {
        background: linear-gradient(145deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
        border: 1px solid rgba(240, 147, 251, 0.2);
        border-radius: 16px;
        padding: 20px;
        margin: 10px 0;
        backdrop-filter: blur(10px);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #a8a8b3;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .insight-card {
        background: linear-gradient(145deg, rgba(240, 147, 251, 0.1), rgba(245, 87, 108, 0.05));
        border-left: 4px solid #f093fb;
        border-radius: 0 12px 12px 0;
        padding: 16px 20px;
        margin: 12px 0;
    }
    
    .positive {
        color: #00d4aa;
    }
    
    .negative {
        color: #ff6b6b;
    }
    
    .neutral {
        color: #ffd93d;
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        border-right: 1px solid rgba(240, 147, 251, 0.1);
    }
    
    .stSelectbox label, .stMultiSelect label, .stSlider label {
        color: #e8d5b7 !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(255,255,255,0.02);
        border-radius: 12px;
        padding: 4px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 8px;
        color: #a8a8b3;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(240, 147, 251, 0.2), rgba(245, 87, 108, 0.1)) !important;
        color: #f093fb !important;
    }
    
    .factor-bar {
        height: 24px;
        border-radius: 12px;
        margin: 4px 0;
    }
    
    div[data-testid="stMarkdownContainer"] p {
        color: #d0d0d8;
    }
</style>
""", unsafe_allow_html=True)


def fetch_api(endpoint: str, method: str = "GET", params: dict = None, json_data: dict = None) -> Optional[Dict]:
    """Fetch data from API."""
    try:
        with httpx.Client(timeout=30.0) as client:
            url = f"{API_BASE_URL}{endpoint}"
            if method == "GET":
                response = client.get(url, params=params)
            else:
                response = client.post(url, params=params, json=json_data)
            
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"API Error: {response.status_code}")
                return None
    except Exception as e:
        st.error(f"Connection error: {e}")
        return None


def render_metric_card(label: str, value: str, change: str = None, change_type: str = "neutral"):
    """Render a styled metric card."""
    change_html = ""
    if change:
        change_class = "positive" if change_type == "positive" else ("negative" if change_type == "negative" else "neutral")
        change_html = f'<span class="{change_class}">{change}</span>'
    
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {change_html}
    </div>
    """, unsafe_allow_html=True)


def render_influence_chart(factors: List[Dict]) -> go.Figure:
    """Render influence factors horizontal bar chart."""
    if not factors:
        return None
    
    df = pd.DataFrame(factors)
    
    colors = ['#f093fb' if row['impact_direction'] == 'positive' else '#ff6b6b' if row['impact_direction'] == 'negative' else '#ffd93d'
              for _, row in df.iterrows()]
    
    fig = go.Figure(go.Bar(
        x=df['influence_score'],
        y=df['indicator_name'],
        orientation='h',
        marker=dict(
            color=colors,
            line=dict(color='rgba(255,255,255,0.3)', width=1)
        ),
        text=df['influence_score'].round(1),
        textposition='inside',
        textfont=dict(color='white', size=12),
        hovertemplate="<b>%{y}</b><br>Score: %{x:.1f}<br>Correlation: %{customdata[0]:.3f}<extra></extra>",
        customdata=df[['correlation']].values
    ))
    
    fig.update_layout(
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e8d5b7', family='DM Sans'),
        yaxis=dict(
            title="",
            categoryorder='total ascending',
            gridcolor='rgba(255,255,255,0.05)'
        ),
        xaxis=dict(
            title="Influence Score",
            gridcolor='rgba(255,255,255,0.05)',
            range=[0, 100]
        ),
        margin=dict(l=20, r=20, t=20, b=40)
    )
    
    return fig


def render_correlation_heatmap(correlations: List[Dict], countries: List[str]) -> go.Figure:
    """Render correlation heatmap across countries."""
    if not correlations:
        return None
    
    # Create pivot table
    indicators = list(set(c['indicator'] for c in correlations if c.get('indicator')))[:8]
    
    # Build matrix
    matrix = []
    for country in countries[:6]:
        row = []
        country_corrs = {c['indicator']: c['correlation'] for c in correlations 
                        if c.get('country') == country}
        for ind in indicators:
            row.append(country_corrs.get(ind, 0))
        matrix.append(row)
    
    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=indicators,
        y=countries[:6],
        colorscale=[
            [0, '#ff6b6b'],
            [0.5, '#1a1a2e'],
            [1, '#00d4aa']
        ],
        zmid=0,
        text=[[f'{v:.2f}' for v in row] for row in matrix],
        texttemplate='%{text}',
        textfont=dict(size=10, color='white'),
        hovertemplate='Country: %{y}<br>Indicator: %{x}<br>Correlation: %{z:.3f}<extra></extra>'
    ))
    
    fig.update_layout(
        height=350,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e8d5b7', family='DM Sans'),
        xaxis=dict(tickangle=45),
        margin=dict(l=20, r=20, t=20, b=80)
    )
    
    return fig


def render_trade_forecast_chart(forecasts: List[Dict]) -> go.Figure:
    """Render trade forecast chart."""
    if not forecasts:
        return None
    
    df = pd.DataFrame(forecasts)
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Import Growth Forecast", "Export Growth Forecast"),
        specs=[[{"type": "bar"}, {"type": "bar"}]]
    )
    
    countries = df['country_code'].unique()[:6]
    colors = px.colors.qualitative.Pastel
    
    for i, country in enumerate(countries):
        country_data = df[df['country_code'] == country]
        
        fig.add_trace(
            go.Bar(
                x=country_data['year'],
                y=country_data['predicted_import_growth'],
                name=country,
                marker_color=colors[i % len(colors)],
                legendgroup=country,
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=country_data['year'],
                y=country_data['predicted_export_growth'],
                name=country,
                marker_color=colors[i % len(colors)],
                legendgroup=country,
                showlegend=False
            ),
            row=1, col=2
        )
    
    fig.update_layout(
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e8d5b7', family='DM Sans'),
        barmode='group',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.25,
            xanchor='center',
            x=0.5
        ),
        margin=dict(l=40, r=40, t=60, b=80)
    )
    
    for i in range(1, 3):
        fig.update_xaxes(gridcolor='rgba(255,255,255,0.05)', row=1, col=i)
        fig.update_yaxes(
            gridcolor='rgba(255,255,255,0.05)',
            title="Growth (%)",
            row=1, col=i
        )
    
    return fig


def render_scenario_chart(scenario_data: List[Dict]) -> go.Figure:
    """Render scenario analysis waterfall chart."""
    if not scenario_data:
        return None
    
    df = pd.DataFrame(scenario_data)
    
    fig = go.Figure(go.Waterfall(
        name="Impact",
        orientation="v",
        x=df['scenario'],
        y=df['change_from_base'],
        text=df['pct_change'].apply(lambda x: f"{x:+.1f}%"),
        textposition="outside",
        connector={"line": {"color": "rgba(255,255,255,0.2)"}},
        increasing={"marker": {"color": "#00d4aa"}},
        decreasing={"marker": {"color": "#ff6b6b"}},
        totals={"marker": {"color": "#f093fb"}}
    ))
    
    fig.update_layout(
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e8d5b7', family='DM Sans'),
        xaxis=dict(tickangle=45, gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(title="Change in Trade Value", gridcolor='rgba(255,255,255,0.05)'),
        margin=dict(l=40, r=40, t=40, b=100)
    )
    
    return fig


def render_demographic_impact(demo_data: List[Dict]) -> go.Figure:
    """Render demographic impact scatter plot."""
    if not demo_data:
        return None
    
    df = pd.DataFrame(demo_data)
    
    fig = px.scatter(
        df,
        x='female_population',
        y='working_age_female',
        size='urbanization_rate',
        color='country_code',
        hover_data=['year', 'female_ratio'],
        labels={
            'female_population': 'Female Population (M)',
            'working_age_female': 'Working Age Female (M)',
            'urbanization_rate': 'Urban %'
        }
    )
    
    fig.update_layout(
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e8d5b7', family='DM Sans'),
        xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
        legend=dict(
            bgcolor='rgba(0,0,0,0.3)',
            bordercolor='rgba(255,255,255,0.1)'
        ),
        margin=dict(l=40, r=40, t=40, b=40)
    )
    
    return fig


def main():
    """Main dashboard application."""
    
    # Header
    st.markdown("# 📊 Macro Trade Analyzer")
    st.markdown("### Women's Apparel Trade Intelligence")
    
    # Sidebar
    with st.sidebar:
        st.markdown("## ⚙️ Analysis Settings")
        
        # Initialize data button
        if st.button("🔄 Initialize/Refresh Data", use_container_width=True):
            with st.spinner("Loading data..."):
                result = fetch_api("/macro/collect", method="POST")
                if result:
                    st.success("Data loaded successfully!")
                    st.rerun()
        
        st.markdown("---")
        
        # Country selection
        countries_data = fetch_api("/macro/countries")
        all_countries = [c['code'] for c in countries_data.get('countries', [])] if countries_data else []
        
        selected_countries = st.multiselect(
            "Select Countries",
            options=all_countries,
            default=all_countries[:5] if all_countries else [],
            help="Choose countries for analysis"
        )
        
        # Target selection
        target = st.selectbox(
            "Analysis Target",
            options=["import_value", "export_value", "import_growth", "export_growth"],
            format_func=lambda x: x.replace("_", " ").title()
        )
        
        st.markdown("---")
        
        # Quick stats
        status = fetch_api("/macro/status")
        if status:
            st.markdown("### 📈 Data Status")
            st.markdown(f"**Countries:** {status.get('countries_available', 0)}")
            st.markdown(f"**Indicators:** {status.get('indicators_available', 0)}")
            st.markdown(f"**Products:** {status.get('product_categories', 0)}")
    
    # Main content tabs
    tabs = st.tabs([
        "🎯 Key Insights",
        "📊 Influence Analysis",
        "🔮 Predictions",
        "🌍 Country Comparison",
        "📦 Product Analysis",
        "📄 Report"
    ])
    
    # Tab 1: Key Insights - Consultant Edition
    with tabs[0]:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(240,147,251,0.1), rgba(245,87,108,0.05)); 
                    padding: 20px; border-radius: 16px; margin-bottom: 20px; border-left: 4px solid #f093fb;">
            <h4 style="color: #f093fb; margin: 0 0 10px 0;">📋 Consultant Analysis: How Macroeconomic Factors Affect Women's Apparel Trade</h4>
            <p style="color: #d0d0d8; margin: 0;">
                This analysis explains the <strong>mechanisms</strong> through which economic indicators impact trade volumes,
                with actionable recommendations for sourcing, pricing, and market strategy.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Market Context Banner
        st.markdown("""
        <div style="background: rgba(255,107,107,0.1); padding: 15px; border-radius: 12px; margin-bottom: 20px; border: 1px solid rgba(255,107,107,0.3);">
            <strong style="color: #ff6b6b;">⚠️ 2025-2026 Market Context:</strong>
            <span style="color: #d0d0d8;">
                Global fashion growth in low single digits • U.S. tariffs 25-35% on China/Mexico imports • 
                >60% of shoppers seeking to reduce fashion expenses • Resale market growing 10-12% annually
            </span>
        </div>
        """, unsafe_allow_html=True)
        
        # Fetch data for analysis
        insights = fetch_api("/macro/insights", params={"top_n": 5})
        import_factors = fetch_api("/macro/influence-factors", params={"target": "import_value", "top_n": 10})
        
        # Create insights engine
        insights_engine = get_insights_engine()
        
        # Key Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        
        if insights:
            with col1:
                render_metric_card("Top Trade Driver", "GDP Growth", "High sensitivity", "positive")
            with col2:
                render_metric_card("Key Risk", "Inflation", "Margin pressure", "negative")
            with col3:
                render_metric_card("Consumer Signal", "Confidence", "Leading indicator", "neutral")
            with col4:
                render_metric_card("Policy Risk", "Tariffs", "Supply chain shift", "negative")
        
        st.markdown("---")
        
        # Main Indicator Analysis - Consultant Format
        st.markdown("## 🔍 How Each Indicator Affects Trade")
        
        # Select indicator for deep dive
        indicator_options = list(INDICATOR_IMPACTS.keys())
        indicator_names = {k: v['name'] for k, v in INDICATOR_IMPACTS.items()}
        
        selected_indicator = st.selectbox(
            "Select Indicator for Deep Analysis",
            options=indicator_options,
            format_func=lambda x: indicator_names.get(x, x),
            key="deep_analysis_indicator"
        )
        
        if selected_indicator:
            impact_info = INDICATOR_IMPACTS.get(selected_indicator, {})
            
            # Correlation data
            corr_value = 0.0
            elasticity_value = 0.0
            if import_factors:
                for factor in import_factors.get('influence_factors', []):
                    if factor.get('indicator', '').lower() == selected_indicator.lower():
                        corr_value = factor.get('correlation', 0)
                        elasticity_value = factor.get('elasticity', 0)
                        break
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Impact header
                direction_icon = "🔺" if impact_info.get('direction') == 'positive' else "🔻" if impact_info.get('direction') == 'negative' else "↔️"
                sensitivity_color = "#ff6b6b" if impact_info.get('sensitivity') == 'very high' else "#ffd93d" if impact_info.get('sensitivity') == 'high' else "#00d4aa"
                
                st.markdown(f"""
                <div style="background: linear-gradient(145deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
                            border-radius: 16px; padding: 24px; border: 1px solid rgba(240,147,251,0.2);">
                    <h3 style="color: #f093fb; margin: 0 0 5px 0;">{direction_icon} {impact_info.get('name', selected_indicator)}</h3>
                    <p style="color: {sensitivity_color}; margin: 0 0 15px 0; font-size: 0.9rem;">
                        Sensitivity: <strong>{impact_info.get('sensitivity', 'medium').title()}</strong> | 
                        Impact Lag: <strong>{impact_info.get('lag_months', 3)} months</strong>
                    </p>
                    <div style="color: #e8d5b7; line-height: 1.7;">
                        {impact_info.get('mechanism', 'No mechanism data available.').replace(chr(10), '<br>')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                # Statistics box
                st.markdown(f"""
                <div style="background: rgba(0,212,170,0.1); border-radius: 12px; padding: 20px; text-align: center;">
                    <div style="color: #a8a8b3; font-size: 0.8rem; text-transform: uppercase;">Correlation with Trade</div>
                    <div style="font-size: 2.5rem; font-weight: 700; color: {'#00d4aa' if corr_value > 0 else '#ff6b6b'};">
                        {corr_value:+.3f}
                    </div>
                    <div style="color: #a8a8b3; margin-top: 10px; font-size: 0.8rem; text-transform: uppercase;">Elasticity</div>
                    <div style="font-size: 1.5rem; font-weight: 600; color: #e8d5b7;">
                        {elasticity_value:+.2f}%
                    </div>
                    <p style="color: #a8a8b3; font-size: 0.75rem; margin-top: 10px;">
                        A 1% change in this indicator<br>leads to ~{abs(elasticity_value):.1f}% change in trade
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            # Recommendations
            st.markdown("### 📌 Recommended Actions")
            recommendations = impact_info.get('recommendations', [])
            
            cols = st.columns(len(recommendations) if len(recommendations) <= 3 else 3)
            for i, rec in enumerate(recommendations[:3]):
                with cols[i]:
                    st.markdown(f"""
                    <div style="background: rgba(240,147,251,0.08); padding: 16px; border-radius: 12px; height: 100%; border: 1px solid rgba(240,147,251,0.15);">
                        <strong style="color: #f093fb;">Action {i+1}</strong>
                        <p style="color: #d0d0d8; margin: 8px 0 0 0; font-size: 0.9rem;">{rec}</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Quick Reference: All Indicators Summary
        st.markdown("## 📊 Indicator Impact Summary")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Positive Drivers (↑ = Trade ↑)")
            for ind_key, ind_info in INDICATOR_IMPACTS.items():
                if ind_info.get('direction') == 'positive':
                    sens = ind_info.get('sensitivity', 'medium')
                    sens_emoji = "🔴" if sens == 'very high' else "🟡" if sens == 'high' else "🟢"
                    st.markdown(f"{sens_emoji} **{ind_info['name']}** - {sens.title()} sensitivity")
        
        with col2:
            st.markdown("### Negative Drivers (↑ = Trade ↓)")
            for ind_key, ind_info in INDICATOR_IMPACTS.items():
                if ind_info.get('direction') == 'negative':
                    sens = ind_info.get('sensitivity', 'medium')
                    sens_emoji = "🔴" if sens == 'very high' else "🟡" if sens == 'high' else "🟢"
                    st.markdown(f"{sens_emoji} **{ind_info['name']}** - {sens.title()} sensitivity")
        
        # Visual comparison chart
        st.markdown("---")
        st.markdown("### 📈 Import vs Export Influence Comparison")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📥 Import Trade Drivers")
            if import_factors:
                fig = render_influence_chart(import_factors.get('influence_factors', []))
                if fig:
                    st.plotly_chart(fig, use_container_width=True, key="import_drivers_chart")
        
        with col2:
            st.markdown("#### 📤 Export Trade Drivers")
            export_factors = fetch_api("/macro/influence-factors", params={"target": "export_value", "top_n": 10})
            if export_factors:
                fig = render_influence_chart(export_factors.get('influence_factors', []))
                if fig:
                    st.plotly_chart(fig, use_container_width=True, key="export_drivers_chart")
    
    # Tab 2: Influence Analysis - Consultant Edition
    with tabs[1]:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(0,212,170,0.1), rgba(0,212,170,0.02)); 
                    padding: 20px; border-radius: 16px; margin-bottom: 20px; border-left: 4px solid #00d4aa;">
            <h4 style="color: #00d4aa; margin: 0 0 10px 0;">📊 Detailed Influence Analysis</h4>
            <p style="color: #d0d0d8; margin: 0;">
                Quantitative analysis of correlation, elasticity, and influence scores with 
                <strong>actionable interpretations</strong> for each indicator.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            analysis_country = st.selectbox(
                "Select Country for Detailed Analysis",
                options=["Global"] + selected_countries,
                key="influence_country"
            )
        
        with col2:
            analysis_target = st.selectbox(
                "Target Metric",
                options=["import_value", "export_value"],
                format_func=lambda x: x.replace("_", " ").title(),
                key="influence_target"
            )
        
        country_param = None if analysis_country == "Global" else analysis_country
        factors = fetch_api("/macro/influence-factors", params={
            "target": analysis_target,
            "country": country_param,
            "top_n": 15
        })
        
        if factors:
            col1, col2 = st.columns([3, 2])
            
            with col1:
                fig = render_influence_chart(factors.get('influence_factors', []))
                if fig:
                    st.plotly_chart(fig, use_container_width=True, key="detailed_influence_chart")
            
            with col2:
                st.markdown("#### 🎯 Factor Analysis with Interpretation")
                
                for factor in factors.get('influence_factors', [])[:6]:
                    indicator = factor.get('indicator', '')
                    impact_info = INDICATOR_IMPACTS.get(indicator, {})
                    magnitude = factor.get('magnitude', 'medium')
                    icon = "🔴" if magnitude == "high" else ("🟡" if magnitude == "medium" else "🟢")
                    direction = "+" if factor.get('impact_direction') == 'positive' else "-"
                    corr = factor.get('correlation', 0)
                    elast = factor.get('elasticity', 0)
                    
                    # Generate interpretation
                    if abs(corr) > 0.5:
                        strength = "Strong"
                    elif abs(corr) > 0.3:
                        strength = "Moderate"
                    else:
                        strength = "Weak"
                    
                    interpretation = f"{strength} {'positive' if corr > 0 else 'negative'} relationship"
                    
                    st.markdown(f"""
                    <div style="background: rgba(255,255,255,0.03); padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 3px solid {'#00d4aa' if corr > 0 else '#ff6b6b'};">
                        <strong style="color: #e8d5b7;">{icon} {factor.get('indicator_name', '')}</strong>
                        <div style="display: flex; gap: 15px; margin-top: 5px;">
                            <span style="color: #a8a8b3; font-size: 0.85rem;">r = {corr:.3f}</span>
                            <span style="color: #a8a8b3; font-size: 0.85rem;">ε = {direction}{abs(elast):.1f}%</span>
                        </div>
                        <p style="color: #d0d0d8; margin: 8px 0 0 0; font-size: 0.8rem;">
                            {interpretation}. When this rises 1%, trade changes ~{abs(elast):.1f}%.
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Key Insight Box
        st.markdown("---")
        st.markdown("""
        <div style="background: rgba(255,215,0,0.1); padding: 20px; border-radius: 12px; border: 1px solid rgba(255,215,0,0.3);">
            <h4 style="color: #ffd700; margin: 0 0 10px 0;">💡 Key Insight: What This Means</h4>
            <p style="color: #d0d0d8; margin: 0;">
                <strong>For Import Trade:</strong> GDP growth and consumer confidence are leading indicators—when they rise, 
                import volumes follow within 2-3 months. Conversely, high inflation and unemployment create headwinds that 
                reduce discretionary spending on apparel.
            </p>
            <p style="color: #d0d0d8; margin: 10px 0 0 0;">
                <strong>For Export Trade:</strong> Exchange rates and trade policies (tariffs) have the most immediate impact. 
                A weaker domestic currency makes exports more competitive, while new tariffs force supply chain restructuring.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Demographics section with interpretation
        st.markdown("---")
        st.markdown("### 👥 Demographic Impact Analysis")
        
        st.markdown("""
        <div style="background: rgba(240,147,251,0.05); padding: 15px; border-radius: 12px; margin-bottom: 15px;">
            <strong style="color: #f093fb;">Why Demographics Matter for Women's Apparel:</strong>
            <ul style="color: #d0d0d8; margin: 10px 0 0 0;">
                <li><strong>Female Population:</strong> Direct market size driver—more women = larger addressable market</li>
                <li><strong>Working-Age Females (15-64):</strong> Peak spending demographic with higher disposable income</li>
                <li><strong>Urbanization:</strong> Urban consumers have 2-3x fashion spending vs. rural</li>
                <li><strong>Female Labor Participation:</strong> Higher workforce participation = higher discretionary income</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        demo_data = fetch_api("/macro/data/demographics", params={"limit": 200})
        if demo_data and demo_data.get('data'):
            fig = render_demographic_impact(demo_data['data'])
            if fig:
                st.plotly_chart(fig, use_container_width=True, key="demographic_impact_chart")
    
    # Tab 3: Predictions
    with tabs[2]:
        st.markdown("### 🔮 Trade Predictions & Scenario Analysis")
        
        pred_tab1, pred_tab2 = st.tabs(["📈 Forecast", "🎛️ Scenario Analysis"])
        
        with pred_tab1:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                years_ahead = st.slider("Forecast Years", 1, 5, 3)
            with col2:
                gdp_assumption = st.slider("GDP Growth Assumption (%)", -2.0, 8.0, 2.5, 0.5)
            with col3:
                inflation_assumption = st.slider("Inflation Assumption (%)", 0.0, 10.0, 2.0, 0.5)
            
            if st.button("Generate Forecast", type="primary"):
                with st.spinner("Generating forecasts..."):
                    forecasts = fetch_api("/macro/forecast", method="POST", json_data={
                        "years_ahead": years_ahead,
                        "countries": selected_countries if selected_countries else None,
                        "gdp_growth_assumption": gdp_assumption,
                        "inflation_assumption": inflation_assumption
                    })
                    
                    if forecasts and forecasts.get('forecasts'):
                        fig = render_trade_forecast_chart(forecasts['forecasts'])
                        if fig:
                            st.plotly_chart(fig, use_container_width=True, key="forecast_chart")
                        
                        # Summary table
                        st.markdown("#### Forecast Summary")
                        df = pd.DataFrame(forecasts['forecasts'])
                        st.dataframe(
                            df[['country_code', 'year', 'predicted_import_growth', 'predicted_export_growth']].round(2),
                            use_container_width=True
                        )
        
        with pred_tab2:
            st.markdown("#### Economic Scenario Simulator")
            
            col1, col2 = st.columns(2)
            
            with col1:
                scenario_gdp = st.number_input("GDP (Billion USD)", value=1000.0, step=100.0)
                scenario_inflation = st.number_input("Inflation (%)", value=2.0, step=0.5)
                scenario_unemployment = st.number_input("Unemployment (%)", value=5.0, step=0.5)
                scenario_consumer_conf = st.number_input("Consumer Confidence", value=100.0, step=5.0)
            
            with col2:
                scenario_clothing_cpi = st.number_input("Clothing CPI", value=100.0, step=2.0)
                scenario_female_pop = st.number_input("Female Population (M)", value=50.0, step=5.0)
                scenario_urban_rate = st.number_input("Urbanization Rate (%)", value=70.0, step=5.0)
                scenario_interest = st.number_input("Interest Rate (%)", value=3.0, step=0.25)
            
            if st.button("Run Scenario Prediction", type="primary"):
                with st.spinner("Running prediction..."):
                    result = fetch_api("/macro/predict/scenario", method="POST", json_data={
                        "gdp": scenario_gdp,
                        "gdp_growth": 2.5,
                        "inflation": scenario_inflation,
                        "unemployment": scenario_unemployment,
                        "consumer_confidence": scenario_consumer_conf,
                        "clothing_cpi": scenario_clothing_cpi,
                        "interest_rate": scenario_interest,
                        "female_population": scenario_female_pop,
                        "working_age_female": scenario_female_pop * 0.65,
                        "urbanization_rate": scenario_urban_rate
                    })
                    
                    if result:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            import_pred = result.get('predictions', {}).get('import_value', {})
                            st.metric(
                                "Predicted Import Value",
                                f"${import_pred.get('prediction', 0):,.0f}M",
                                help="Predicted total import value in millions USD"
                            )
                        
                        with col2:
                            export_pred = result.get('predictions', {}).get('export_value', {})
                            st.metric(
                                "Predicted Export Value",
                                f"${export_pred.get('prediction', 0):,.0f}M",
                                help="Predicted total export value in millions USD"
                            )
    
    # Tab 4: Country Comparison
    with tabs[3]:
        st.markdown("### 🌍 Country Comparison Analysis")
        
        if selected_countries:
            comparison_data = []
            
            for country in selected_countries[:6]:
                country_analysis = fetch_api(f"/macro/analysis/country/{country}")
                if country_analysis:
                    comparison_data.append({
                        "country": country,
                        "data": country_analysis
                    })
            
            if comparison_data:
                # Build comparison table
                comparison_rows = []
                for item in comparison_data:
                    import_drivers = item['data'].get('import_analysis', {}).get('top_drivers', [])
                    export_drivers = item['data'].get('export_analysis', {}).get('top_drivers', [])
                    
                    comparison_rows.append({
                        "Country": item['country'],
                        "Top Import Driver": import_drivers[0].get('indicator_name', 'N/A') if import_drivers else 'N/A',
                        "Import Driver Score": import_drivers[0].get('influence_score', 0) if import_drivers else 0,
                        "Top Export Driver": export_drivers[0].get('indicator_name', 'N/A') if export_drivers else 'N/A',
                        "Export Driver Score": export_drivers[0].get('influence_score', 0) if export_drivers else 0,
                    })
                
                comparison_df = pd.DataFrame(comparison_rows)
                st.dataframe(comparison_df, use_container_width=True)
                
                # Visual comparison
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    name='Import Influence',
                    x=comparison_df['Country'],
                    y=comparison_df['Import Driver Score'],
                    marker_color='#f093fb'
                ))
                
                fig.add_trace(go.Bar(
                    name='Export Influence',
                    x=comparison_df['Country'],
                    y=comparison_df['Export Driver Score'],
                    marker_color='#00d4aa'
                ))
                
                fig.update_layout(
                    barmode='group',
                    height=400,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#e8d5b7', family='DM Sans'),
                    xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
                    yaxis=dict(title="Influence Score", gridcolor='rgba(255,255,255,0.05)'),
                    legend=dict(orientation='h', y=-0.15)
                )
                
                st.plotly_chart(fig, use_container_width=True, key="country_comparison_chart")
        else:
            st.info("Please select countries from the sidebar to compare")
    
    # Tab 5: Product Analysis
    with tabs[4]:
        st.markdown("### 📦 Product Category Analysis")
        
        products = fetch_api("/macro/products")
        if products:
            product_list = products.get('products', [])
            
            # Product overview
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("#### Available Categories")
                for product in product_list:
                    category_icon = {
                        "formal": "👔",
                        "casual": "👕",
                        "tops": "👚",
                        "underwear": "🩱",
                        "knitwear": "🧶",
                        "activewear": "🏃‍♀️",
                        "accessories": "🧣"
                    }.get(product.get('category', ''), "📦")
                    
                    st.markdown(f"{category_icon} **{product.get('name', '')}**")
                    st.caption(f"HS Code: {product.get('hs_code', '')}")
            
            with col2:
                # Trade data by product
                trade_data = fetch_api("/macro/data/trade", params={"limit": 500})
                if trade_data and trade_data.get('data'):
                    df = pd.DataFrame(trade_data['data'])
                    
                    # Aggregate by product
                    product_summary = df.groupby('hs_code').agg({
                        'import_value': 'sum',
                        'export_value': 'sum'
                    }).reset_index()
                    
                    # Add product names
                    product_dict = {p['hs_code']: p['name'] for p in product_list}
                    product_summary['product_name'] = product_summary['hs_code'].map(product_dict)
                    
                    fig = px.bar(
                        product_summary,
                        x='product_name',
                        y=['import_value', 'export_value'],
                        barmode='group',
                        labels={'value': 'Trade Value', 'product_name': 'Product Category'}
                    )
                    
                    fig.update_layout(
                        height=400,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#e8d5b7', family='DM Sans'),
                        xaxis=dict(tickangle=45),
                        legend=dict(title="", orientation='h', y=-0.3)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True, key="product_trade_chart")
    
    # Tab 6: Report
    with tabs[5]:
        st.markdown("### 📄 Analysis Report")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if st.button("📥 Generate Full Report", type="primary", use_container_width=True):
                with st.spinner("Generating report..."):
                    report = fetch_api("/macro/report")
                    if report:
                        st.session_state['full_report'] = report.get('report', '')
            
            st.markdown("---")
            
            if st.button("🤖 Get AI Insights", use_container_width=True):
                with st.spinner("Generating AI insights..."):
                    ai_insights = fetch_api("/macro/llm/insights", params={"analysis_type": "executive"})
                    if ai_insights:
                        st.session_state['ai_insights'] = ai_insights.get('insight', '')
        
        with col2:
            if 'full_report' in st.session_state:
                st.markdown(st.session_state['full_report'])
            
            if 'ai_insights' in st.session_state:
                st.markdown("---")
                st.markdown("### 🤖 AI-Generated Insights")
                st.markdown(st.session_state['ai_insights'])
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666; font-size: 0.8rem;'>"
        f"Women's Apparel Macro Trade Analyzer | Data updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        "Powered by Economic Intelligence"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
